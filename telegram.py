import requests
from config import Config

def send_otp(chat_id, code):
    url = f'https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage'
    text = (
        f"🔐 *XarajatTrack — Tasdiqlash kodi*\n\n"
        f"Kodingiz: *{code}*\n\n"
        f"⏱ 5 daqiqa amal qiladi."
    )
    try:
        r = requests.post(url, json={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}, timeout=5)
        return r.json().get('ok', False)
    except:
        return False
    