import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import json
import time
import logging
import html
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ─── Configuration ───
BOT_TOKEN           = "8513071962:AAEuk7UOeKn1eV8rzCuB9B7giHbkAIudNG"
CHAT_ID             = "-1003247504066"
OWNER_ID            = 7095358778
NUMBER_BOT_HTTP_URL = "http://localhost:8080/otp"

NUMBER_CHANNEL_URL  = "https://t.me/EARNING_HUB_NUMBER_BOT"
MAIN_CHANNEL_URL    = "https://t.me/earning_hub_otp_group"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/140.0 Mobile Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest'
}

SERVICE_PATTERNS = {
    'WhatsApp':  r'whatsapp|واتساب|watsapp',
    'Telegram':  r'telegram',
    'Facebook':  r'facebook|fb\.com|meta',
    'Instagram': r'instagram|ig\b',
    'Twitter':   r'twitter|x\.com',
    'TikTok':    r'tiktok|tik tok',
    'Snapchat':  r'snapchat',
    'Google':    r'google|gmail|youtube',
    'Microsoft': r'microsoft|outlook|hotmail|msn|xbox',
    'Apple':     r'apple|icloud|itunes',
    'Amazon':    r'amazon',
    'PayPal':    r'paypal',
    'Binance':   r'binance',
    'Uber':      r'\buber\b',
    'Bolt':      r'\bbolt\b',
    'Netflix':   r'netflix',
    'OTP':       r'verification|verify|otp|code|كود|رمز|pin\b|passcode',
}

OTP_HISTORY_FILE = "otp_history.json"
PANELS_FILE      = "panels.json"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)
active_tasks = {}

PANEL_TYPE_LABEL = {
    "masdar_client": "Masdar Client",
    "masdar_agent":  "Masdar Agent",
    "ims_client":    "IMS Client",
    "ims_agent":     "IMS Agent",
}

# ════════════════════════════════════════
# ─── Login Functions ───
# ════════════════════════════════════════

async def _masdar_login(session, url, username, password) -> bool:
    try:
        async with session.get(f"{url}/ints/login", ssl=False, timeout=15) as r:
            if r.status != 200: return False
            soup = BeautifulSoup(await r.text(), "html.parser")
            capt = "5"
            inp  = soup.find("input", {"name": "capt"})
            if inp:
                nums = re.findall(r'\d+', (inp.find_parent("div") or inp).get_text())
                if len(nums) >= 2:
                    capt = str(int(nums[0]) + int(nums[1]))
        async with session.post(
            f"{url}/ints/signin",
            data={"username": username, "password": password, "capt": capt},
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": f"{url}/ints/login", "Origin": url},
            allow_redirects=True, ssl=False, timeout=15
        ) as r:
            if "login" not in str(r.url).lower():
                LOGGER.info(f"✅ Masdar login OK: {url}")
                return True
            return False
    except Exception as e:
        LOGGER.debug(f"Masdar login skip: {e}")
        return False

async def _ims_login(session, url, username, password) -> bool:
    try:
        async with session.get(f"{url}/login", ssl=False, timeout=15) as r:
            if r.status != 200: return False
            text = await r.text()
            soup = BeautifulSoup(text, "html.parser")
            capt = "5"
            math = re.search(r'(\d+)\s*([\+\-])\s*(\d+)', text)
            if math:
                a, op, b = int(math.group(1)), math.group(2), int(math.group(3))
                capt = str(a + b) if op == '+' else str(a - b)
            etkk     = soup.find("input", {"name": "etkk"})
            etkk_val = etkk.get("value", "") if etkk else ""
        async with session.post(
            f"{url}/signin",
            data={"etkk": etkk_val, "username": username, "password": password, "capt": capt},
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Referer": f"{url}/login"},
            allow_redirects=True, ssl=False, timeout=15
        ) as r:
            text = await r.text()
            if username in text or "CDR" in text or "dashboard" in str(r.url).lower():
                LOGGER.info(f"✅ IMS login OK: {url}")
                return True
            return False
    except Exception as e:
        LOGGER.debug(f"IMS login skip: {e}")
        return False

async def auto_login(session, url, username, password) -> bool:
    if await _masdar_login(session, url, username, password):
        return True
    if await _ims_login(session, url, username, password):
        return True
    return False


# ════════════════════════════════════════
# ─── Fetch SMS ───
# ════════════════════════════════════════

TYPE_MAP = {
    "masdar_client": {"path": "/ints/client/res/data_smscdr.php",
                      "ref":  "/ints/client/SMSCDRStats", "cols": 7, "idx": 4},
    "masdar_agent":  {"path": "/ints/agent/res/data_smscdr.php",
                      "ref":  "/ints/agent/SMSCDRStats",  "cols": 7, "idx": 4},
    "ims_client":    {"path": "/client/res/data_smscdr.php",
                      "ref":  "/client/SMSCDRStats",      "cols": 9, "idx": 5},
    "ims_agent":     {"path": "/agent/res/data_smscdr.php",
                      "ref":  "/agent/SMSCDRReports",     "cols": 9, "idx": 5},
}

async def fetch_sms(session, url, panel_type) -> list:
    cfg   = TYPE_MAP.get(panel_type)
    if not cfg: return []
    today = datetime.now().strftime('%Y-%m-%d')
    ts    = int(time.time() * 1000)
    params = {
        "fdate1": f"{today} 00:00:00",
        "fdate2": f"{today} 23:59:59",
        "frange": "", "fnum": "", "fcli": "", "fg": "0",
        "sEcho": "1", "iColumns": str(cfg["cols"]),
        "iDisplayStart": "0", "iDisplayLength": "100",
        "sSearch": "", "bRegex": "false",
        "iSortCol_0": "0", "sSortDir_0": "desc", "iSortingCols": "1",
        "_": ts,
    }
    for i in range(cfg["cols"]):
        params[f"mDataProp_{i}"] = str(i)
    try:
        async with session.get(
            url + cfg["path"], params=params, ssl=False, timeout=15,
            headers={"X-Requested-With": "XMLHttpRequest",
                     "Referer": url + cfg["ref"]}
        ) as r:
            if r.status != 200: return []
            data   = json.loads(await r.text())
            result = []
            for item in data.get("aaData", []):
                if not isinstance(item, list) or len(item) <= cfg["idx"]: continue
                if isinstance(item[0], str) and item[0].startswith('0,0,0,0'): continue
                otp = extract_otp(str(item[cfg["idx"]]))
                if otp:
                    cn, cf = extract_country_info(str(item[2]) if len(item) > 2 else "")
                    result.append({
                        "timestamp":     str(item[0]),
                        "range":         str(item[1]) if len(item) > 1 else "",
                        "number":        re.sub(r"\D", "", str(item[2])) if len(item) > 2 else "",
                        "service":       str(item[3]) if len(item) > 3 else "",
                        "message":       str(item[cfg["idx"]]),
                        "otp":           otp,
                        "country":       cn,
                        "country_emoji": cf,
                    })
            return result
    except Exception as e:
        LOGGER.error(f"❌ fetch_sms error: {e}")
        return []


# ════════════════════════════════════════
# ─── Helpers ───
# ════════════════════════════════════════

def extract_otp(message: str):
    if not message: return None
    cleaned = re.sub(r'\b(19|20)\d{2}[-/]\d{2}[-/]\d{2}\b', '', message)
    cleaned = re.sub(r'\b(19|20)\d{2}\b', '', cleaned)
    for p in [
        r'FB-(\d{5})', r'[Gg]-(\d{6})',
        r'Facebook.*?[#]?\s*(\d{4,6})', r'[#]?\s*(\d{4,6})\s+.*Facebook',
        r'Bolt.*?code\s+(\d{4})', r'use code\s+(\d{4})',
        r'واتساب.*?(\d{3}[- ]?\d{3})', r'كود.*?(\d{3}[- ]?\d{3})',
        r'WhatsApp.*?(\d{3}[- ]?\d{3})', r'kode.*?(\d{3}[- ]?\d{3})',
        r'(?:otp|code|pin|verification|كود|رمز)[^\d]{0,15}(\d{4,8})',
        r'\b(\d{6})\b', r'\b(\d{4,8})\b',
    ]:
        m = re.search(p, cleaned, re.IGNORECASE)
        if m:
            raw = m.group(1).replace(' ', '').replace('-', '')
            if 4 <= len(raw) <= 8:
                return raw
    return None

def detect_service(message: str, range_name: str = "") -> str:
    combined = (message + " " + range_name).lower()
    for svc, pat in SERVICE_PATTERNS.items():
        if re.search(pat, combined, re.IGNORECASE):
            return svc
    return "Other"

def extract_country_info(phone_number: str):
    try:
        clean = re.sub(r'\D', '', str(phone_number)).lstrip('0')
        if not clean: return "Unknown", "🌍"
        CC = {
            '1':'US','20':'EG','211':'SS','212':'MA','213':'DZ','216':'TN','218':'LY',
            '220':'GM','221':'SN','222':'MR','223':'ML','224':'GN','225':'CI','226':'BF',
            '227':'NE','228':'TG','229':'BJ','230':'MU','231':'LR','232':'SL','233':'GH',
            '234':'NG','235':'TD','236':'CF','237':'CM','238':'CV','240':'GQ','241':'GA',
            '242':'CG','243':'CD','244':'AO','245':'GW','248':'SC','249':'SD','250':'RW',
            '251':'ET','252':'SO','253':'DJ','254':'KE','255':'TZ','256':'UG','257':'BI',
            '258':'MZ','260':'ZM','261':'MG','263':'ZW','264':'NA','265':'MW','266':'LS',
            '267':'BW','268':'SZ','27':'ZA','291':'ER','30':'GR','31':'NL','32':'BE',
            '33':'FR','34':'ES','351':'PT','352':'LU','353':'IE','354':'IS','355':'AL',
            '356':'MT','357':'CY','358':'FI','359':'BG','36':'HU','370':'LT','371':'LV',
            '372':'EE','373':'MD','374':'AM','375':'BY','380':'UA','381':'RS','382':'ME',
            '383':'XK','385':'HR','386':'SI','387':'BA','389':'MK','39':'IT','40':'RO',
            '41':'CH','420':'CZ','421':'SK','43':'AT','44':'GB','45':'DK','46':'SE',
            '47':'NO','48':'PL','49':'DE','501':'BZ','502':'GT','503':'SV','504':'HN',
            '505':'NI','506':'CR','507':'PA','509':'HT','51':'PE','52':'MX','53':'CU',
            '54':'AR','55':'BR','56':'CL','57':'CO','58':'VE','591':'BO','592':'GY',
            '593':'EC','595':'PY','597':'SR','598':'UY','60':'MY','61':'AU','62':'ID',
            '63':'PH','64':'NZ','65':'SG','66':'TH','670':'TL','673':'BN','675':'PG',
            '679':'FJ','7':'RU','81':'JP','82':'KR','84':'VN','86':'CN','880':'BD',
            '90':'TR','91':'IN','92':'PK','93':'AF','94':'LK','95':'MM','98':'IR',
            '960':'MV','961':'LB','962':'JO','963':'SY','964':'IQ','965':'KW','966':'SA',
            '967':'YE','968':'OM','971':'AE','972':'IL','973':'BH','974':'QA','977':'NP',
            '992':'TJ','993':'TM','994':'AZ','995':'GE','996':'KG','998':'UZ',
        }
        NAMES = {
            'US':'USA','GB':'UK','IN':'India','BD':'Bangladesh','DE':'Germany','FR':'France',
            'IT':'Italy','ES':'Spain','BR':'Brazil','RU':'Russia','CN':'China','JP':'Japan',
            'KR':'South Korea','SG':'Singapore','MY':'Malaysia','AE':'UAE','SA':'Saudi Arabia',
            'PK':'Pakistan','TZ':'Tanzania','AU':'Australia','NG':'Nigeria','GH':'Ghana',
            'KE':'Kenya','ZA':'South Africa','EG':'Egypt','TL':'Timor-Leste','BF':'Burkina Faso',
            'TR':'Turkey','ID':'Indonesia','PH':'Philippines','VN':'Vietnam','TH':'Thailand',
        }
        for l in range(4, 0, -1):
            code = clean[:l]
            if code in CC:
                iso  = CC[code]
                name = NAMES.get(iso, iso)
                flag = chr(ord(iso[0])+127397)+chr(ord(iso[1])+127397) if len(iso)==2 else "🌍"
                return name, flag
        return "Unknown", "🌍"
    except:
        return "Unknown", "🌍"

def mask_phone(number: str) -> str:
    digits = re.findall(r'\d', str(number))
    if len(digits) <= 8: return str(number)
    return f"{''.join(digits[:4])}SPYX{''.join(digits[-4:])}"

def format_otp_message(sms: dict) -> str:
    country = html.escape(sms.get('country', 'Unknown'))
    flag    = sms.get('country_emoji', '🌍')
    service = html.escape(sms.get('service', 'Unknown'))
    masked  = html.escape(mask_phone(sms.get('number', '')))
    if not service or service in ('Other', 'OTP'):
        b = re.search(r'\[([^\]]+)\]', sms.get('message', ''))
        service = html.escape(b.group(1)) if b else 'Unknown'
    return (
        f"{service} | {flag} {country}\n"
        f"───────────────────────────\n"
        f"☎️ Number: <code>{masked}</code>"
    )

def make_otp_buttons(otp_code=None):
    kb = []
    if otp_code:
        kb.append([{"text": str(otp_code), "copy_text": {"text": str(otp_code)}}])
    kb.append([
        {"text": "☎️ Numbers", "url": NUMBER_CHANNEL_URL},
        {"text": "💬 Chats",   "url": MAIN_CHANNEL_URL}
    ])
    return {"inline_keyboard": kb}

async def send_tg(message: str, reply_markup=None, retries=5):
    url     = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
    if reply_markup:
        payload['reply_markup'] = reply_markup
    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.post(url, json=payload, timeout=15) as r:
                    if r.status == 200:
                        return (await r.json()).get('result', {}).get('message_id')
                    elif r.status == 429:
                        ra = (await r.json()).get("parameters", {}).get("retry_after", 5)
                        await asyncio.sleep(ra + 1)
                    elif r.status == 400:
                        return None
        except Exception as e:
            LOGGER.error(f"TG send error: {e}")
            if attempt < retries:
                await asyncio.sleep(3)
    return None

async def notify_number_bot(number: str, otp: str, service: str):
    payload = {
        "number":  re.sub(r"\D", "", str(number)),
        "otp":     re.sub(r"[\s\-]", "", str(otp)),
        "service": str(service).lower().split()[0] if service else "other"
    }
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(NUMBER_BOT_HTTP_URL, json=payload,
                              headers={"Content-Type": "application/json"}, timeout=10) as r:
                await r.text()
    except:
        pass


# ════════════════════════════════════════
# ─── OTP History ───
# ════════════════════════════════════════

async def load_history():
    try:
        with open(OTP_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

async def save_history(history):
    try:
        with open(OTP_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        LOGGER.error(f"History save error: {e}")

async def is_new_otp(sms: dict) -> bool:
    history = await load_history()
    otp_id  = f"{sms['number']}_{sms['otp']}_{sms['timestamp']}"
    return otp_id not in history

async def mark_otp(sms: dict):
    history = await load_history()
    otp_id  = f"{sms['number']}_{sms['otp']}_{sms['timestamp']}"
    history[otp_id] = {
        "otp": sms['otp'], "number": sms['number'],
        "service": sms.get('service', ''), "timestamp": sms['timestamp'],
        "bot_received_time": datetime.now().isoformat()
    }
    await save_history(history)


# ════════════════════════════════════════
# ─── Panel Monitor ───
# ════════════════════════════════════════

async def monitor_panel(panel: dict, idx: int):
    url        = panel["url"].rstrip("/")
    username   = panel["username"]
    password   = panel["password"]
    panel_type = panel.get("type", "masdar_client")

    LOGGER.info(f"🚀 Panel #{idx+1} [{PANEL_TYPE_LABEL.get(panel_type, panel_type)}] started: {url}")

    history       = await load_history()
    today_str     = datetime.now().strftime('%Y-%m-%d')
    previous_otps = set(k for k in history if today_str in history[k].get('timestamp', ''))
    last_login    = 0
    fail_count    = 0

    async with aiohttp.ClientSession(
        headers=HEADERS, cookie_jar=aiohttp.CookieJar(unsafe=True)
    ) as session:
        while True:
            try:
                if time.time() - last_login > 540:
                    ok = await auto_login(session, url, username, password)
                    if not ok:
                        fail_count += 1
                        if fail_count >= 3:
                            LOGGER.error(f"❌ Panel #{idx+1} login failed 3x, stopping")
                            return
                        await asyncio.sleep(60)
                        continue
                    last_login = time.time()
                    fail_count = 0

                sms_list = await fetch_sms(session, url, panel_type)

                for sms in sms_list:
                    otp_id = f"{sms['number']}_{sms['otp']}_{sms['timestamp']}"
                    if otp_id in previous_otps:
                        continue
                    previous_otps.add(otp_id)
                    if not await is_new_otp(sms):
                        continue

                    sms['service'] = detect_service(sms['message'], sms.get('range', ''))
                    msg_id = await send_tg(format_otp_message(sms), reply_markup=make_otp_buttons(sms['otp']))
                    if msg_id:
                        LOGGER.info(f"✅ OTP sent: {sms['number']} - {sms['otp']}")
                        await notify_number_bot(sms['number'], sms['otp'], sms['service'])
                    await mark_otp(sms)
                    await asyncio.sleep(2)

                if len(previous_otps) > 5000:
                    previous_otps = set(list(previous_otps)[-2000:])

                await asyncio.sleep(1)

            except asyncio.CancelledError:
                LOGGER.info(f"⏹️ Panel #{idx+1} stopped")
                return
            except Exception as e:
                LOGGER.error(f"❌ Panel #{idx+1} error: {e}")
                await asyncio.sleep(30)


# ════════════════════════════════════════
# ─── Panel Data ───
# ════════════════════════════════════════

def load_panels() -> list:
    try:
        with open(PANELS_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_panels(panels: list):
    with open(PANELS_FILE, "w") as f:
        json.dump(panels, f, indent=2)

def is_admin(user_id) -> bool:
    return str(user_id) == str(OWNER_ID)

def start_panel(panel: dict, idx: int):
    active_tasks[idx] = asyncio.create_task(monitor_panel(panel, idx))


# ════════════════════════════════════════
# ─── Telegram Handlers ───
# ════════════════════════════════════════

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Masdar Client", callback_data="add_masdar_client"),
         InlineKeyboardButton("➕ Masdar Agent",  callback_data="add_masdar_agent")],
        [InlineKeyboardButton("➕ IMS Client",    callback_data="add_ims_client"),
         InlineKeyboardButton("➕ IMS Agent",     callback_data="add_ims_agent")],
        [InlineKeyboardButton("📋 Panel List",    callback_data="list_panels"),
         InlineKeyboardButton("🗑️ Delete",        callback_data="del_panel")],
        [InlineKeyboardButton("📊 Status",        callback_data="status")],
    ])

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("❌ Access Denied")
    context.user_data.clear()
    await update.message.reply_text("🤖 *OTP Bot Panel Manager*", parse_mode="Markdown", reply_markup=main_menu())

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except: pass
    if not is_admin(update.effective_user.id): return

    data   = query.data
    panels = load_panels()

    if data.startswith("add_"):
        ptype = data[4:]
        context.user_data["state"]      = "waiting_panel"
        context.user_data["panel_type"] = ptype
        label = PANEL_TYPE_LABEL.get(ptype, ptype)
        await query.edit_message_text(
            f"➕ *{label} Panel যোগ করো*\n\n"
            f"Format: `URL username password`\n\n"
            f"Example:\n`http://139.99.69.196 admin admin123`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="main_menu")
            ]])
        )

    elif data == "main_menu":
        context.user_data.clear()
        await query.edit_message_text("🤖 *OTP Bot Panel Manager*",
            parse_mode="Markdown", reply_markup=main_menu())

    elif data == "list_panels":
        if not panels:
            text = "📋 কোনো panel নেই।"
        else:
            text = "📋 *Panel List:*\n\n"
            for i, p in enumerate(panels):
                running = i in active_tasks and not active_tasks[i].done()
                label   = PANEL_TYPE_LABEL.get(p.get('type', ''), p.get('type', ''))
                text   += f"*{i+1}.* `{p['url']}`\n👤 `{p['username']}` | 🏷️ {label} | {'🟢 Running' if running else '🔴 Stopped'}\n\n"
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))

    elif data == "del_panel":
        if not panels:
            return await query.edit_message_text("❌ কোনো panel নেই।",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
        buttons = [[InlineKeyboardButton(
            f"🗑️ {i+1}. {p['url']} [{PANEL_TYPE_LABEL.get(p.get('type',''), '')}]",
            callback_data=f"del_confirm_{i}")] for i, p in enumerate(panels)]
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        await query.edit_message_text("🗑️ *কোন panel delete করবে?*",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("del_confirm_"):
        idx = int(data.split("_")[-1])
        if 0 <= idx < len(panels):
            removed = panels.pop(idx)
            save_panels(panels)
            if idx in active_tasks and not active_tasks[idx].done():
                active_tasks[idx].cancel()
                active_tasks.pop(idx, None)
            await query.edit_message_text(f"✅ *Deleted:* `{removed['url']}`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))

    elif data == "status":
        text = f"📊 *Bot Status*\n\n🗂️ Total: *{len(panels)}*\n\n"
        for i, p in enumerate(panels):
            running = i in active_tasks and not active_tasks[i].done()
            label   = PANEL_TYPE_LABEL.get(p.get('type', ''), '')
            text   += f"{'🟢' if running else '🔴'} *{i+1}.* `{p['url']}` [{label}]\n"
        await query.edit_message_text(text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="status")],
                [InlineKeyboardButton("🔙 Back",    callback_data="main_menu")]
            ]))

async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if context.user_data.get("state") == "waiting_panel":
        context.user_data["state"] = None
        parts = update.message.text.strip().split()
        if len(parts) != 3:
            return await update.message.reply_text(
                "❌ Format ভুল!\n`URL username password`", parse_mode="Markdown")
        url, username, password = parts
        ptype  = context.user_data.pop("panel_type", "masdar_client")
        panel  = {"url": url, "username": username, "password": password, "type": ptype}
        panels = load_panels()
        panels.append(panel)
        save_panels(panels)
        idx = len(panels) - 1
        start_panel(panel, idx)
        label = PANEL_TYPE_LABEL.get(ptype, ptype)
        await update.message.reply_text(
            f"✅ *Panel Added & Started!*\n\n"
            f"🔗 `{url}`\n👤 `{username}`\n🏷️ {label}",
            parse_mode="Markdown", reply_markup=main_menu()
        )


# ════════════════════════════════════════
# ─── Main ───
# ════════════════════════════════════════

async def send_start_alert():
    msg = (
        "<b>🤖 OTP Bot Started ✅</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>⏰ Time:</b> <code>{datetime.now().strftime('%I:%M:%S %p')}</code>\n"
        f"<b>📅 Date:</b> <code>{datetime.now().strftime('%d-%m-%Y')}</code>\n"
        f"<b>🤵 Owner:</b> <code>{OWNER_ID}</code>\n"
        "<b>📡 OTP Scrapper:</b> Running...\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    await send_tg(msg)

async def main():
    print("🤖 OTP Bot Starting...")
    panels = load_panels()
    for i, p in enumerate(panels):
        start_panel(p, i)

    tg_app = Application.builder().token(BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("start", cmd_start))
    tg_app.add_handler(CallbackQueryHandler(cb_handler))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))

    await send_start_alert()
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling(allowed_updates=["message", "callback_query"])
    LOGGER.info("✅ Bot fully started!")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped.")
