import requests
import json
from config import Config

TELEGRAM_API = f"https://api.telegram.org/bot{Config.BOT_TOKEN}"

# ─── Xabar yuborish ───────────────────────────────────────────────────────────
def send_message(chat_id, text, keyboard=None, parse_mode="Markdown"):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload, timeout=10)
        return r.json().get("ok", False)
    except Exception as e:
        print(f"[send_message error] {e}")
        return False

# ─── OTP yuborish (parolni tiklash uchun) ────────────────────────────────────
def send_otp(chat_id, code):
    text = (
        f"🔐 *XarajatTrack — Tasdiqlash kodi*\n\n"
        f"Kodingiz: *{code}*\n\n"
        f"⏱ 5 daqiqa amal qiladi."
    )
    return send_message(chat_id, text)

# ─── Menyular ─────────────────────────────────────────────────────────────────
def user_keyboard():
    return {
        "keyboard": [
            [{"text": "📱 XarajatTrack Ilovasi", "web_app": {"url": Config.WEBAPP_URL}}]
        ],
        "resize_keyboard": True
    }

def admin_keyboard():
    return {
        "keyboard": [
            [{"text": "📱 XarajatTrack Ilovasi", "web_app": {"url": Config.WEBAPP_URL}}],
            [{"text": "🤖 AI bilan suhbat"}, {"text": "📈 Trading Robot"}],
            [{"text": "🏠 Bosh menyu"}]
        ],
        "resize_keyboard": True
    }

def send_user_menu(chat_id, text):
    send_message(chat_id, text, user_keyboard())

def send_admin_menu(chat_id, text):
    send_message(chat_id, text, admin_keyboard())

# ─── Groq AI bilan suhbat ────────────────────────────────────────────────────
def ask_groq(user_message):
    if not Config.GROQ_API_KEY:
        return "❌ Groq API kaliti topilmadi."
    try:
        headers = {
            "Authorization": f"Bearer {Config.GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Siz XarajatTrack ilovasining AI yordamchisisiz. "
                        "Foydalanuvchilarga moliyaviy maslahatlar bering, "
                        "xarajatlarni boshqarishda yordam bering. "
                        "Qisqa, aniq va do'stona javob bering. O'zbek tilida gaplashing."
                    )
                },
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=30
        )
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Groq error] {e}")
        return "❌ AI javob bera olmadi. Keyinroq urinib ko'ring."

# ─── Foydalanuvchi holati (xotira) ───────────────────────────────────────────
# Oddiy dict — Render restart qilganda tozalanadi, lekin yetarli
user_states = {}  # {chat_id: "MAIN_MENU" | "AI_CHAT"}
admin_users = set()  # Admin chat_id lar ro'yxati

# ─── Asosiy webhook handler ───────────────────────────────────────────────────
def handle_update(update):
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = str(message.get("chat", {}).get("id", ""))
    text = message.get("text", "").strip()

    if not chat_id or not text:
        return

    is_admin = chat_id in admin_users
    state = user_states.get(chat_id, "MAIN_MENU")

    # /start buyrug'i
    if text == "/start":
        user_states[chat_id] = "MAIN_MENU"
        greeting = (
            f"Assalomu alaykum! XarajatTrack ga xush kelibsiz! 👋\n\n"
            f"🆔 Sizning Telegram Chat ID: `{chat_id}`\n\n"
            f"Saytdan ro'yxatdan o'tishda shu raqamni ishlating!"
        )
        if is_admin:
            send_admin_menu(chat_id, greeting)
        else:
            send_user_menu(chat_id, greeting)
        return

    # Admin maxfiy so'z
    if text == Config.SECRET_WORD:
        admin_users.add(chat_id)
        user_states[chat_id] = "MAIN_MENU"
        send_admin_menu(chat_id, "✅ Admin huquqi berildi! Barcha imkoniyatlar ochiq. 👑")
        return

    # Bosh menyu
    if text == "🏠 Bosh menyu":
        user_states[chat_id] = "MAIN_MENU"
        if is_admin:
            send_admin_menu(chat_id, "🏠 Bosh menyudasiz.")
        else:
            send_user_menu(chat_id, "🏠 Bosh menyudasiz.")
        return

    # AI bilan suhbat (faqat adminlar uchun)
    if text == "🤖 AI bilan suhbat":
        if not is_admin:
            send_message(chat_id, "❌ Bu funksiya faqat adminlar uchun.")
            return
        user_states[chat_id] = "AI_CHAT"
        send_message(chat_id, "🚀 *Groq AI (Llama) ishga tushdi!* Savolingizni yozing.\n\n_(Chiqish uchun: 🏠 Bosh menyu)_", admin_keyboard())
        return

    # Trading Robot menusi
    if text == "📈 Trading Robot":
        if not is_admin:
            send_message(chat_id, "❌ Bu funksiya faqat adminlar uchun.")
            return
        
        # Robot haqida holat xabari
        bot_msg = (
            "📈 *AI Trading Robot — Bildirishnomalar Paneli*\n\n"
            f"Sizning Chat ID raqamingiz: `{chat_id}`\n\n"
            "Bu ID ni kompyuteringizdagi `robot_settings.json` faylining `telegram_chat_id` qismiga kiritishingiz kerak. "
            "Shundan so'ng, noutbukingizdagi AI Savdo Roboti barcha ochiq va yopiq orderlar, "
            "hamda Qizil Xavf (Yangiliklar) haqida to'g'ridan-to'g'ri shu botga jonli xabarlar yuborib turadi!\n\n"
            "✅ *Aloqa kanali ochiq va tayyor!*"
        )
        send_message(chat_id, bot_msg, admin_keyboard())
        return

    # AI suhbat holati
    if state == "AI_CHAT" and is_admin:
        send_message(chat_id, "⏳ AI javob tayyorlamoqda...")
        answer = ask_groq(text)
        send_message(chat_id, f"🤖 {answer}", admin_keyboard())
        return

    # Boshqa xabarlar
    if is_admin:
        send_admin_menu(chat_id, "👆 Quyidagi tugmalardan birini tanlang:")
    else:
        send_user_menu(chat_id, "👆 Ilovani ochish uchun tugmani bosing:")

# ─── Webhookni o'rnatish ──────────────────────────────────────────────────────
def set_webhook(webhook_url):
    url = f"{TELEGRAM_API}/setWebhook"
    payload = {
        "url": webhook_url,
        "allowed_updates": ["message", "edited_message"]
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        result = r.json()
        print(f"[setWebhook] {result}")
        return result.get("ok", False)
    except Exception as e:
        print(f"[setWebhook error] {e}")
        return False