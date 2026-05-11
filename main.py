import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
import json
import time
import logging
import html
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# Configuration
MASDAR_URL = "http://139.99.69.196"
USERNAME = "Waleedbhai"
PASSWORD = "Waleedbhai"

# Telegram Configuration
BOT_TOKEN = "8513071962:AAEuk7UOeKn1eV8rzCuB9B7giHbkAIudNGM"
CHAT_ID = "-1003247504066"
OWNER_ID = 7095358778

# Number Bot HTTP URL
NUMBER_BOT_HTTP_URL = "https://t.me/Secure_otp_hub_bot"

# Telegram Button URLs
NUMBER_CHANNEL_URL = "https://t.me/EARNING_HUB_NUMBER_BOT"
MAIN_CHANNEL_URL   = "https://t.me/earning_hub_otp_group"

# Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; Infinix X6525B Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.207 Mobile Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9,bn-BD;q=0.8,bn;q=0.7',
    'X-Requested-With': 'XMLHttpRequest'
}

# Service patterns for OTP detection
SERVICE_PATTERNS = {
    'WhatsApp':   r'whatsapp|واتساب|watsapp',
    'Telegram':   r'telegram',
    'Facebook':   r'facebook|fb\.com|meta',
    'Instagram':  r'instagram|ig\b',
    'Twitter':    r'twitter|x\.com',
    'TikTok':     r'tiktok|tik tok',
    'Snapchat':   r'snapchat',
    'LinkedIn':   r'linkedin',
    'Google':     r'google|gmail|youtube',
    'Microsoft':  r'microsoft|outlook|hotmail|msn|xbox|live\.com',
    'Apple':      r'apple|icloud|itunes|app store',
    'Amazon':     r'amazon',
    'PayPal':     r'paypal',
    'Binance':    r'binance',
    'Uber':       r'\buber\b',
    'Bolt':       r'\bbolt\b',
    'Netflix':    r'netflix',
    'OTP':        r'verification|verify|otp|code|كود|رمز|pin\b|passcode',
}

# File paths
OTP_HISTORY_FILE = "otp_history.json"
PANELS_FILE      = "panels.json"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger(__name__)

class MasdarAlkonOTPBot:
    def __init__(self):
        self.base_url = MASDAR_URL
        self.session = None
        self.last_login_time = 0
        
    async def start_session(self):
        self.session = aiohttp.ClientSession(
            headers=HEADERS,
            cookie_jar=aiohttp.CookieJar(unsafe=True)
        )
        
    async def close_session(self):
        if self.session:
            await self.session.close()
    
    async def auto_login_with(self, url, username, password):
        try:
            LOGGER.info(f"🔐 Logging in to: {url} ({username})")
            self.base_url = url

            await self.close_session()
            await self.start_session()

            async with self.session.get(f'{url}/ints/login', ssl=False) as response:
                html_resp = await response.text()
                soup = BeautifulSoup(html_resp, 'html.parser')

                captcha_answer = "5"
                captcha_input  = soup.find('input', {'name': 'capt'})
                if captcha_input:
                    parent_div = captcha_input.find_parent('div')
                    if parent_div:
                        captcha_text = parent_div.get_text(strip=True)
                        numbers      = re.findall(r'\d+', captcha_text)
                        if len(numbers) >= 2:
                            captcha_answer = str(int(numbers[0]) + int(numbers[1]))

                login_data = {'username': username, 'password': password, 'capt': captcha_answer}
                headers    = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Referer': f'{url}/ints/login',
                    'Origin':  url
                }

                async with self.session.post(
                    f'{url}/ints/signin',
                    data=login_data, headers=headers,
                    allow_redirects=True, ssl=False
                ) as resp:
                    final_url = str(resp.url)
                    if "login" not in final_url.lower():
                        LOGGER.info(f"🎉 Login Successful: {url}")
                        self.last_login_time = time.time()
                        return True
                    else:
                        LOGGER.error(f"❌ Login Failed: {url}")
                        return False

        except Exception as e:
            LOGGER.error(f"❌ Login error ({url}): {e}")
            return False

    async def get_sms_data_api(self):
        try:
            timestamp = int(time.time() * 1000)
            today = datetime.now()
            start_date_obj = today
            end_date_obj = today

            start_date = f"{start_date_obj.strftime('%Y-%m-%d')}%2000:00:00"
            end_date   = f"{end_date_obj.strftime('%Y-%m-%d')}%2023:59:59"

            api_url = (
                f"{self.base_url}/ints/client/res/data_smscdr.php?"
                f"fdate1={start_date}&fdate2={end_date}&"
                f"frange=&fnum=&fcli=&fgdate=&fgmonth=&fgrange=&fgnumber=&fgcli=&fg=0&"
                f"sEcho=1&iColumns=7&sColumns=%2C%2C%2C%2C%2C%2C&"
                f"iDisplayStart=0&iDisplayLength=100&"
                f"mDataProp_0=0&sSearch_0=&bRegex_0=false&bSearchable_0=true&bSortable_0=true&"
                f"mDataProp_1=1&sSearch_1=&bRegex_1=false&bSearchable_1=true&bSortable_1=true&"
                f"mDataProp_2=2&sSearch_2=&bRegex_2=false&bSearchable_2=true&bSortable_2=true&"
                f"mDataProp_3=3&sSearch_3=&bRegex_3=false&bSearchable_3=true&bSortable_3=true&"
                f"mDataProp_4=4&sSearch_4=&bRegex_4=false&bSearchable_4=true&bSortable_4=true&"
                f"mDataProp_5=5&sSearch_5=&bRegex_5=false&bSearchable_5=true&bSortable_5=true&"
                f"mDataProp_6=6&sSearch_6=&bRegex_6=false&bSearchable_6=true&bSortable_6=true&"
                f"sSearch=&bRegex=false&iSortCol_0=0&sSortDir_0=desc&iSortingCols=1&_={timestamp}"
            )

            api_headers = {
                'User-Agent': HEADERS['User-Agent'],
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'{self.base_url}/ints/client/SMSCDRStats'
            }

            async with self.session.get(api_url, headers=api_headers, ssl=False) as response:
                if response.status == 200:
                    response_text = await response.text()
                    try:
                        data = json.loads(response_text)
                        total_records = int(data.get('iTotalRecords', 0))

                        if total_records > 0:
                            sms_list =[]
                            for item in data.get("aaData",[]):
                                if isinstance(item, list) and len(item) >= 5 and isinstance(item[0], str):
                                    if item[0].startswith('0,0,0,0'):
                                        continue
                                    
                                    otp_code = self.extract_otp(item[4])
                                    if otp_code:
                                        country_name, country_emoji = self.extract_country_info(item[2])
                                        sms_entry = {
                                            'timestamp':     item[0],
                                            'range':         item[1],
                                            'number':        item[2],
                                            'service':       item[3],
                                            'message':       item[4],
                                            'otp':           otp_code,
                                            'country':       country_name,
                                            'country_emoji': country_emoji
                                        }
                                        sms_list.append(sms_entry)
                            return sms_list
                        else:
                            return[]
                    except json.JSONDecodeError:
                        return[]
                else:
                    return[]

        except Exception as e:
            LOGGER.error(f"❌ API fetch error: {e}")
            return[]
    
    def extract_otp(self, message):
        if not message:
            return None
            
        facebook_patterns =[
            r'Facebook.*?[#]?\s*(\d{4,6})', r'[#]?\s*(\d{4,6})\s+.*Facebook',
            r'FB.*?[#]?\s*(\d{4,6})', r'[#]?\s*(\d{4,6})\s+.*FB', r'FB-(\d{5}).*Facebook'
        ]
        for pattern in facebook_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match: return match.group(1)
        
        bolt_patterns =[r'Bolt.*?code\s+(\d{4})', r'code\s+(\d{4}).*?Bolt', r'use code\s+(\d{4})']
        for pattern in bolt_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match: return match.group(1)
        
        whatsapp_patterns =[
            r'واتساب.*?(\d{3}[- ]?\d{3})', r'(\d{3}[- ]?\d{3}).*?واتساب',
            r'كود.*?(\d{3}[- ]?\d{3})', r'(\d{3}[- ]?\d{3}).*?كود'
        ]
        for pattern in whatsapp_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match: return match.group(1)
        
        afrikaans_patterns =[
            r'WhatsApp.*?(\d{3}[- ]?\d{3})', r'(\d{3}[- ]?\d{3}).*?WhatsApp',
            r'kode.*?(\d{3}[- ]?\d{3})', r'(\d{3}[- ]?\d{3}).*?kode'
        ]
        for pattern in afrikaans_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match: return match.group(1)
        
        universal_patterns =[
            r'\b(\d{4,6})\b', r'\b(\d{3}[- ]?\d{3})\b', r'[#]?\s*(\d{4,6})\s', r'\s(\d{4,6})\s'
        ]
        for pattern in universal_patterns:
            match = re.search(pattern, message)
            if match:
                otp = match.group(1)
                if otp and re.match(r'^\d+$', otp.replace(' ', '').replace('-', '')):
                    return otp
        return None
    
    def extract_country_info(self, phone_number):
        if not phone_number:
            return "Unknown", "🌍"
        try:
            clean_number = re.sub(r'\D', '', str(phone_number)).lstrip('0')
            if not clean_number: return "Unknown", "🌍"
            
            EXTENDED_COUNTRY_CODES = {
                '1': 'US', '1242': 'BS', '1246': 'BB', '1264': 'AI', '1268': 'AG', '1284': 'VG',
                '1340': 'VI', '1441': 'BM', '1473': 'GD', '1649': 'TC', '1664': 'MS', '1670': 'MP',
                '1671': 'GU', '1684': 'AS', '1758': 'LC', '1767': 'DM', '1784': 'VC', '1787': 'PR',
                '1809': 'DO', '1868': 'TT', '1869': 'KN', '1876': 'JM', '20': 'EG', '211': 'SS',
                '212': 'MA', '213': 'DZ', '216': 'TN', '218': 'LY', '220': 'GM', '221': 'SN',
                '222': 'MR', '223': 'ML', '224': 'GN', '225': 'CI', '226': 'BF', '227': 'NE',
                '228': 'TG', '229': 'BJ', '230': 'MU', '231': 'LR', '232': 'SL', '233': 'GH',
                '234': 'NG', '235': 'TD', '236': 'CF', '237': 'CM', '238': 'CV', '239': 'ST',
                '240': 'GQ', '241': 'GA', '242': 'CG', '243': 'CD', '244': 'AO', '245': 'GW',
                '246': 'IO', '248': 'SC', '249': 'SD', '250': 'RW', '251': 'ET', '252': 'SO',
                '253': 'DJ', '254': 'KE', '255': 'TZ', '256': 'UG', '257': 'BI', '258': 'MZ',
                '260': 'ZM', '261': 'MG', '262': 'RE', '263': 'ZW', '264': 'NA', '265': 'MW',
                '266': 'LS', '267': 'BW', '268': 'SZ', '269': 'KM', '27': 'ZA', '290': 'SH',
                '291': 'ER', '297': 'AW', '298': 'FO', '299': 'GL', '30': 'GR', '31': 'NL',
                '32': 'BE', '33': 'FR', '34': 'ES', '350': 'GI', '351': 'PT', '352': 'LU',
                '353': 'IE', '354': 'IS', '355': 'AL', '356': 'MT', '357': 'CY', '358': 'FI',
                '359': 'BG', '36': 'HU', '370': 'LT', '371': 'LV', '372': 'EE', '373': 'MD',
                '374': 'AM', '375': 'BY', '376': 'AD', '377': 'MC', '378': 'SM', '379': 'VA',
                '380': 'UA', '381': 'RS', '382': 'ME', '383': 'XK', '385': 'HR', '386': 'SI',
                '387': 'BA', '389': 'MK', '39': 'IT', '40': 'RO', '41': 'CH', '420': 'CZ',
                '421': 'SK', '423': 'LI', '43': 'AT', '44': 'GB', '45': 'DK', '46': 'SE',
                '47': 'NO', '48': 'PL', '49': 'DE', '500': 'FK', '501': 'BZ', '502': 'GT',
                '503': 'SV', '504': 'HN', '505': 'NI', '506': 'CR', '507': 'PA', '508': 'PM',
                '509': 'HT', '51': 'PE', '52': 'MX', '53': 'CU', '54': 'AR', '55': 'BR',
                '56': 'CL', '57': 'CO', '58': 'VE', '590': 'GP', '591': 'BO', '592': 'GY',
                '593': 'EC', '594': 'GF', '595': 'PY', '596': 'MQ', '597': 'SR', '598': 'UY',
                '599': 'CW', '60': 'MY', '61': 'AU', '62': 'ID', '63': 'PH', '64': 'NZ',
                '65': 'SG', '66': 'TH', '670': 'TL', '672': 'NF', '673': 'BN', '674': 'NR',
                '675': 'PG', '676': 'TO', '677': 'SB', '678': 'VU', '679': 'FJ', '680': 'PW',
                '681': 'WF', '682': 'CK', '683': 'NU', '685': 'WS', '686': 'KI', '687': 'NC',
                '688': 'TV', '689': 'PF', '690': 'TK', '691': 'FM', '692': 'MH', '7': 'RU',
                '81': 'JP', '82': 'KR', '84': 'VN', '86': 'CN', '880': 'BD', '90': 'TR',
                '91': 'IN', '92': 'PK', '93': 'AF', '94': 'LK', '95': 'MM', '98': 'IR',
                '960': 'MV', '961': 'LB', '962': 'JO', '963': 'SY', '964': 'IQ', '965': 'KW',
                '966': 'SA', '967': 'YE', '968': 'OM', '970': 'PS', '971': 'AE', '972': 'IL',
                '973': 'BH', '974': 'QA', '975': 'BT', '976': 'MN', '977': 'NP', '992': 'TJ',
                '993': 'TM', '994': 'AZ', '995': 'GE', '996': 'KG', '998': 'UZ'
            }
            
            COUNTRY_NAME_MAP = {
                'US': 'USA', 'GB': 'UK', 'IN': 'India', 'BD': 'Bangladesh', 'CA': 'Canada',
                'TZ': 'Tanzania', 'AU': 'Australia', 'DE': 'Germany', 'FR': 'France', 'IT': 'Italy', 'ES': 'Spain',
                'BR': 'Brazil', 'RU': 'Russia', 'CN': 'China', 'JP': 'Japan', 'KR': 'South Korea',
                'SG': 'Singapore', 'MY': 'Malaysia', 'AE': 'UAE', 'SA': 'Saudi Arabia', 'PK': 'Pakistan',
                'IR': 'Iran', 'MM': 'Myanmar', 'GH': 'Ghana', 'EG': 'Egypt', 'TR': 'Turkey',
                'ID': 'Indonesia', 'PH': 'Philippines', 'VN': 'Vietnam', 'TH': 'Thailand', 'MX': 'Mexico',
                'AR': 'Argentina', 'CL': 'Chile', 'PE': 'Peru', 'CO': 'Colombia', 'VE': 'Venezuela',
                'UA': 'Ukraine', 'PL': 'Poland', 'NL': 'Netherlands', 'BE': 'Belgium', 'SE': 'Sweden',
                'NO': 'Norway', 'DK': 'Denmark', 'FI': 'Finland', 'CH': 'Switzerland', 'AT': 'Austria',
                'PT': 'Portugal', 'GR': 'Greece', 'IL': 'Israel', 'ZA': 'South Africa', 'NG': 'Nigeria',
                'KE': 'Kenya', 'MA': 'Morocco', 'DZ': 'Algeria', 'IQ': 'Iraq', 'LB': 'Lebanon',
                'JO': 'Jordan', 'KW': 'Kuwait', 'QA': 'Qatar', 'OM': 'Oman', 'BH': 'Bahrain',
                'AF': 'Afghanistan', 'BS': 'Bahamas', 'BB': 'Barbados', 'AI': 'Anguilla', 'AG': 'Antigua',
                'VG': 'British Virgin Islands', 'VI': 'US Virgin Islands', 'BM': 'Bermuda', 'GD': 'Grenada',
                'TC': 'Turks and Caicos', 'MS': 'Montserrat', 'MP': 'Northern Mariana', 'GU': 'Guam',
                'AS': 'American Samoa', 'LC': 'Saint Lucia', 'DM': 'Dominica', 'VC': 'Saint Vincent',
                'PR': 'Puerto Rico', 'DO': 'Dominican Republic', 'TT': 'Trinidad', 'KN': 'Saint Kitts',
                'JM': 'Jamaica', 'SS': 'South Sudan', 'LY': 'Libya', 'GM': 'Gambia', 'SN': 'Senegal',
                'MR': 'Mauritania', 'ML': 'Mali', 'GN': 'Guinea', 'CI': 'Ivory Coast', 'BF': 'Burkina Faso',
                'NE': 'Niger', 'TG': 'Togo', 'BJ': 'Benin', 'MU': 'Mauritius', 'LR': 'Liberia',
                'SL': 'Sierra Leone', 'TD': 'Chad', 'CF': 'Central Africa', 'CM': 'Cameroon',
                'CV': 'Cape Verde', 'ST': 'Sao Tome', 'GQ': 'Equatorial Guinea', 'GA': 'Gabon',
                'CG': 'Congo', 'CD': 'DR Congo', 'AO': 'Angola', 'GW': 'Guinea-Bissau', 'IO': 'British Indian Ocean',
                'SC': 'Seychelles', 'RW': 'Rwanda', 'ET': 'Ethiopia', 'SO': 'Somalia', 'DJ': 'Djibouti',
                'UG': 'Uganda', 'BI': 'Burundi', 'MZ': 'Mozambique', 'ZM': 'Zambia',
                'MG': 'Madagascar', 'RE': 'Reunion', 'ZW': 'Zimbabwe', 'NA': 'Namibia', 'MW': 'Malawi',
                'LS': 'Lesotho', 'BW': 'Botswana', 'SZ': 'Eswatini', 'KM': 'Comoros', 'SH': 'Saint Helena',
                'ER': 'Eritrea', 'AW': 'Aruba', 'FO': 'Faroe Islands', 'GL': 'Greenland', 'GI': 'Gibraltar',
                'LU': 'Luxembourg', 'IE': 'Ireland', 'IS': 'Iceland', 'AL': 'Albania', 'MT': 'Malta',
                'BG': 'Bulgaria', 'HU': 'Hungary', 'LT': 'Lithuania', 'LV': 'Latvia', 'EE': 'Estonia',
                'MD': 'Moldova', 'AM': 'Armenia', 'BY': 'Belarus', 'AD': 'Andorra', 'MC': 'Monaco',
                'SM': 'San Marino', 'VA': 'Vatican', 'RS': 'Serbia', 'ME': 'Montenegro', 'XK': 'Kosovo',
                'HR': 'Croatia', 'SI': 'Slovenia', 'BA': 'Bosnia', 'MK': 'North Macedonia', 'RO': 'Romania',
                'CZ': 'Czech Republic', 'SK': 'Slovakia', 'LI': 'Liechtenstein', 'FK': 'Falkland Islands',
                'BZ': 'Belize', 'GT': 'Guatemala', 'SV': 'El Salvador', 'HN': 'Honduras', 'NI': 'Nicaragua',
                'CR': 'Costa Rica', 'PA': 'Panama', 'PM': 'Saint Pierre', 'HT': 'Haiti', 'CU': 'Cuba',
                'BO': 'Bolivia', 'GY': 'Guyana', 'EC': 'Ecuador', 'GF': 'French Guiana', 'PY': 'Paraguay',
                'MQ': 'Martinique', 'SR': 'Suriname', 'UY': 'Uruguay', 'TL': 'Timor-Leste', 'NF': 'Norfolk Island',
                'BN': 'Brunei', 'NR': 'Nauru', 'PG': 'Papua New Guinea', 'TO': 'Tonga', 'SB': 'Solomon Islands',
                'VU': 'Vanuatu', 'FJ': 'Fiji', 'PW': 'Palau', 'WF': 'Wallis and Futuna', 'CK': 'Cook Islands',
                'NU': 'Niue', 'WS': 'Samoa', 'KI': 'Kiribati', 'NC': 'New Caledonia', 'TV': 'Tuvalu',
                'PF': 'French Polynesia', 'TK': 'Tokelau', 'FM': 'Micronesia', 'MH': 'Marshall Islands',
                'MV': 'Maldives', 'SY': 'Syria', 'YE': 'Yemen', 'BT': 'Bhutan', 'MN': 'Mongolia',
                'TJ': 'Tajikistan', 'TM': 'Turkmenistan', 'AZ': 'Azerbaijan', 'GE': 'Georgia', 'KG': 'Kyrgyzstan',
                'UZ': 'Uzbekistan'
            }
            
            for code_length in range(4, 0, -1):
                if len(clean_number) >= code_length:
                    country_code = clean_number[:code_length]
                    if country_code in EXTENDED_COUNTRY_CODES:
                        iso_code = EXTENDED_COUNTRY_CODES[country_code]
                        country_name = COUNTRY_NAME_MAP.get(iso_code, "Unknown")
                        
                        # Dynamically Generate Flag Emoji based on the 2-letter ISO code! No manual dictionary needed!
                        if len(iso_code) == 2:
                            flag_emoji = chr(ord(iso_code[0]) + 127397) + chr(ord(iso_code[1]) + 127397)
                        else:
                            flag_emoji = "🌍"
                            
                        return country_name, flag_emoji
                        
            return "Unknown", "🌍"
        except Exception:
            return "Unknown", "🌍"
    
    def extract_service(self, message, range_name):
        for service, pattern in SERVICE_PATTERNS.items():
            if re.search(pattern, message, re.IGNORECASE):
                return service
        if 'facebook' in range_name.lower() or 'fb' in range_name.lower(): return 'Facebook'
        elif 'whatsapp' in range_name.lower() or 'واتساب' in message.lower(): return 'WhatsApp'
        elif 'telegram' in range_name.lower(): return 'Telegram'
        return "Other"

async def load_otp_history():
    try:
        with open(OTP_HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

async def save_otp_history(history):
    try:
        with open(OTP_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        LOGGER.error(f"❌ History save error: {e}")

async def check_is_new_otp(sms_data):
    history = await load_otp_history()
    otp_id = f"{sms_data['number']}_{sms_data['otp']}_{sms_data['timestamp']}"
    return otp_id not in history

async def save_otp(sms_data):
    history = await load_otp_history()
    current_time = datetime.now().isoformat()
    otp_id = f"{sms_data['number']}_{sms_data['otp']}_{sms_data['timestamp']}"
    history[otp_id] = {
        "otp": sms_data['otp'],
        "number": sms_data['number'],
        "service": sms_data['service'],
        "range": sms_data['range'],
        "country": sms_data['country'],
        "timestamp": sms_data['timestamp'],
        "bot_received_time": current_time
    }
    await save_otp_history(history)

async def send_telegram_message_async(message, reply_markup=None, retries=5):
    url     = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
    if reply_markup:
        payload['reply_markup'] = reply_markup

    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=15) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get('result', {}).get('message_id')
                    
                    elif resp.status == 429: # 🔴 TELEGRAM RATE LIMIT HIT
                        error_data = await resp.json()
                        retry_after = error_data.get("parameters", {}).get("retry_after", 5)
                        LOGGER.warning(f"⚠️ Telegram Rate Limit (429)! Sleeping for {retry_after} seconds...")
                        await asyncio.sleep(retry_after + 1)
                        continue 
                        
                    else:
                        error_text = await resp.text()
                        LOGGER.error(f"❌ Telegram API Error ({resp.status}): {error_text}")
                        if resp.status == 400:
                            return None
        except Exception as e:
            LOGGER.error(f"❌ Telegram Request Exception: {e}")
            if attempt < retries:
                await asyncio.sleep(3)
    return None

def make_otp_buttons(otp_code=None):
    inline_keyboard =[]
    
    # 1. Adds the Telegram "Copy Text" inline button spanning the full width!
    if otp_code:
        inline_keyboard.append([{
            "text": str(otp_code),
            "copy_text": {
                "text": str(otp_code)
            }
        }])
        
    # 2. Adds your standard "Numbers" and "Chats" buttons right below it
    inline_keyboard.append([
        {"text": "☎️ Numbers", "url": NUMBER_CHANNEL_URL},
        {"text": "💬 Chats", "url": MAIN_CHANNEL_URL}
    ])
    
    return {"inline_keyboard": inline_keyboard}

async def notify_number_bot(phone_number: str, otp_code: str, service: str):
    clean_number  = re.sub(r"\D", "", str(phone_number))
    clean_otp     = re.sub(r"[\s\-]", "", str(otp_code))
    clean_service = str(service).lower().split()[0] if service else "other"
    payload = {"number": clean_number, "otp": clean_otp, "service": clean_service}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(NUMBER_BOT_HTTP_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=10) as resp:
                await resp.text()
    except Exception:
        pass

def mask_phone(number: str) -> str:
    try:
        if not number: return ""
        s = str(number)
        digits = re.findall(r'\d', s)
        total = len(digits)
        if total <= 8: return s
        return f"{''.join(digits[:4])}SPYX{''.join(digits[-4:])}"
    except Exception:
        return str(number)

def format_otp_message(sms_data):
    country       = html.escape(str(sms_data.get('country', 'Unknown')))
    country_emoji = sms_data.get('country_emoji', '🌍')
    service       = html.escape(str(sms_data.get('service', 'Unknown')))
    number        = str(sms_data.get('number', ''))

    masked_number = html.escape(mask_phone(number))

    if not service or service == 'Other' or service == 'OTP':
        bracket = re.search(r'\[([^\]]+)\]', sms_data.get('message', ''))
        if bracket:
            service = html.escape(bracket.group(1))
        else:
            service = 'Unknown'

    message = (
        f"{service} | {country_emoji} {country}\n"
        f"───────────────────────────\n"
        f"☎️ Number: <code>{masked_number}</code>"
    )
    return message

async def send_start_alert_async():
    try:
        timestamp = datetime.now().strftime("%I:%M:%S %p")
        date = datetime.now().strftime("%d-%m-%Y")
        message = (
            "<b>🤖 OTP Bot Started Successfully ✅</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>⏰ Time:</b> <code>{timestamp}</code>\n"
            f"<b>📅 Date:</b> <code>{date}</code>\n"
            f"<b>🤵 Owner:</b> <code>{OWNER_ID}</code>\n"
            f"<b>💰 Traffic:</b> Running.....📡\n"
            f"<b>📩 OTP Scrapper:</b> Running...🔍\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Don't Spam Here Just Wait For OTP ❌</b>"
        )
        await send_telegram_message_async(message)
    except Exception as e:
        LOGGER.error(f"❌ Error sending start alert: {e}")

# ════════════════════════════════════════════════
# ✅ PANEL MANAGEMENT SYSTEM
# ════════════════════════════════════════════════

active_tasks = {}

def load_panels():
    try:
        with open(PANELS_FILE, "r") as f:
            return json.load(f)
    except:
        default =[{"url": MASDAR_URL, "username": USERNAME, "password": PASSWORD}]
        save_panels(default)
        return default

def save_panels(panels):
    with open(PANELS_FILE, "w") as f:
        json.dump(panels, f, indent=2)

def is_admin(user_id):
    return str(user_id) == str(OWNER_ID)

def main_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("➕ Add Panel",     callback_data="add_panel")],[InlineKeyboardButton("📋 List Panels",   callback_data="list_panels"),
         InlineKeyboardButton("🗑️ Delete Panel",  callback_data="del_panel")],[InlineKeyboardButton("📊 Status",        callback_data="status")],
    ])

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return await update.message.reply_text("❌ Access Denied")
    context.user_data.clear()
    await update.message.reply_text("🤖 *OTP Bot Panel Manager*", parse_mode="Markdown", reply_markup=main_menu())

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try: await query.answer()
    except: pass
    if not is_admin(update.effective_user.id): return

    panels, data = load_panels(), query.data
    try:
        if data == "main_menu":
            context.user_data.clear()
            await query.edit_message_text("🤖 *OTP Bot Panel Manager*", parse_mode="Markdown", reply_markup=main_menu())
        elif data == "add_panel":
            context.user_data["state"] = "waiting_panel"
            await query.edit_message_text("➕ *Panel যোগ করো*\n\nExample:\n`http://139.99.69.196 admin admin123`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
        elif data == "list_panels":
            text = "📋 *Panel List:*\n\n" if panels else "📋 কোনো panel নেই।"
            for i, p in enumerate(panels):
                running = i in active_tasks and not active_tasks[i].done()
                text   += f"*{i+1}.* `{p['url']}`\n👤 `{p['username']}` | {'🟢 Running' if running else '🔴 Stopped'}\n\n"
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
        elif data == "del_panel":
            if not panels: return await query.edit_message_text("❌ কোনো panel নেই।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
            buttons = [[InlineKeyboardButton(f"🗑️ {i+1}. {p['url']}", callback_data=f"del_confirm_{i}")] for i, p in enumerate(panels)]
            buttons.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
            await query.edit_message_text("🗑️ *কোন panel delete করবে?*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        elif data.startswith("del_confirm_"):
            idx = int(data.split("_")[-1])
            if 0 <= idx < len(panels):
                removed = panels.pop(idx)
                save_panels(panels)
                if idx in active_tasks and not active_tasks[idx].done():
                    active_tasks[idx].cancel()
                    active_tasks.pop(idx, None)
                await query.edit_message_text(f"✅ *Deleted:* `{removed['url']}`", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
        elif data == "status":
            text = f"📊 *Bot Status*\n\n🗂️ Total Panels: *{len(panels)}*\n\n"
            for i, p in enumerate(panels):
                text += f"{'🟢' if (i in active_tasks and not active_tasks[i].done()) else '🔴'} *{i+1}.* `{p['url']}`\n"
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="status")],[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
    except Exception: pass

async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if context.user_data.get("state") == "waiting_panel":
        context.user_data["state"] = None
        parts = update.message.text.strip().split()
        if len(parts) != 3: return await update.message.reply_text("❌ Format ভুল!")
        url, username, password = parts
        panels = load_panels()
        panels.append({"url": url, "username": username, "password": password})
        save_panels(panels)
        idx = len(panels) - 1
        active_tasks[idx] = asyncio.create_task(monitor_single_panel(url, username, password, idx))
        await update.message.reply_text(f"✅ *Panel Added!*\n🔗 URL: `{url}`", parse_mode="Markdown", reply_markup=main_menu())

async def monitor_single_panel(url, username, password, idx):
    LOGGER.info(f"🚀 Panel #{idx+1} monitoring started: {url}")
    bot_instance = MasdarAlkonOTPBot()
    bot_instance.base_url = url

    history = await load_otp_history()
    previous_otps = set(history.keys())

    try:
        while True:
            success = await bot_instance.auto_login_with(url, username, password)
            if not success:
                LOGGER.error(f"❌ Panel #{idx+1} login failed. Retrying in 60s...")
                await asyncio.sleep(60)
                continue

            LOGGER.info(f"✅ Panel #{idx+1} logged in: {url}")

            while True:
                try:
                    if time.time() - bot_instance.last_login_time > 600:
                        if not await bot_instance.auto_login_with(url, username, password):
                            await asyncio.sleep(30)
                            break 

                    sms_result = await bot_instance.get_sms_data_api()

                    for sms in sms_result:
                        otp_id = f"{sms['number']}_{sms['otp']}_{sms['timestamp']}"
                        if otp_id not in previous_otps:
                            is_new = await check_is_new_otp(sms)
                            if is_new:
                                sms['service'] = bot_instance.extract_service(sms['message'], sms['range'])
                                
                                formatted_message = format_otp_message(sms)
                                
                                message_id = await send_telegram_message_async(
                                    formatted_message,
                                    reply_markup=make_otp_buttons(sms['otp'])
                                )
                                
                                if message_id:
                                    LOGGER.info(f"✅ Panel #{idx+1} OTP sent: {sms['number']} - {sms['otp']}")
                                    await notify_number_bot(sms['number'], sms['otp'], sms['service'])
                                else:
                                    LOGGER.error(f"❌ Telegram ultimately rejected the message for {sms['number']}. Marking as seen.")
                                
                                await save_otp(sms)
                                previous_otps.add(otp_id)
                                
                                await asyncio.sleep(3) 

                            else:
                                previous_otps.add(otp_id)

                    if len(previous_otps) > 5000:
                        previous_otps = set(list(previous_otps)[-2000:])

                    await asyncio.sleep(1)

                except asyncio.CancelledError:
                    LOGGER.info(f"⏹️ Panel #{idx+1} stopped")
                    return
                except Exception as e:
                    LOGGER.error(f"❌ Panel #{idx+1} internal iteration error: {e}")
                    await asyncio.sleep(30)
                    break
    except asyncio.CancelledError:
        pass
    finally:
        await bot_instance.close_session()

async def main():
    print("🤖 OTP Bot Panel Manager Starting...")
    print("="*50)

    panels = load_panels()
    for i, p in enumerate(panels):
        active_tasks[i] = asyncio.create_task(monitor_single_panel(p["url"], p["username"], p["password"], i))

    tg_app = Application.builder().token(BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("start", cmd_start))
    tg_app.add_handler(CallbackQueryHandler(cb_handler))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))

    await send_start_alert_async()
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
        print("\n👋 Bot stopped gracefully.")