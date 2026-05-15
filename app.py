from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random
import requests as req
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mening_maxfiy_kalitim')

# PostgreSQL URL ni to'g'rilash
database_url = os.environ.get('DATABASE_URL', 'sqlite:///xarajatlar.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

db = SQLAlchemy(app)

# =================== TELEGRAM SOZLAMA ===================
BOT_TOKEN = os.environ.get('BOT_TOKEN')

def telegram_otp_yuborish(chat_id, code):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    matn = (
        f"🔐 *XarajatTrack — Tasdiqlash kodi*\n\n"
        f"Sizning kodingiz: *{code}*\n\n"
        f"⏱ Bu kod 5 daqiqa amal qiladi.\n"
        f"_Agar siz so'ramagan bo'lsangiz, e'tibor bermang._"
    )
    try:
        javob = req.post(url, json={
            'chat_id': chat_id,
            'text': matn,
            'parse_mode': 'Markdown'
        }, timeout=5)
        return javob.json().get('ok', False)
    except:
        return False

# =================== MODELLAR ===================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    telegram_chat_id = db.Column(db.String(50), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class OTPCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used = db.Column(db.Boolean, default=False)

    def is_valid(self):
        muddati = datetime.utcnow() - timedelta(minutes=5)
        return not self.used and self.created_at > muddati

# =================== ROUTELAR ===================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        telegram_chat_id = request.form.get('telegram_chat_id', '').strip()

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return redirect('/register?error=Bu username allaqachon band!')

        user = User(username=username, telegram_chat_id=telegram_chat_id or None)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return redirect('/?success=Ro\'yxatdan o\'tdingiz! Endi kiring.')

    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session['user_id'] = user.id
        session['username'] = username
        return redirect('/dashboard')

    return redirect('/?error=Login yoki parol xato!')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# =================== PAROL TIKLASH ===================

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()

        if not user:
            return redirect('/forgot-password?error=Bunday foydalanuvchi topilmadi!')

        if not user.telegram_chat_id:
            return redirect('/forgot-password?error=Bu hisobga Telegram bog\'lanmagan!')

        code = str(random.randint(100000, 999999))

        OTPCode.query.filter_by(username=username, used=False).delete()
        db.session.commit()

        otp = OTPCode(username=username, code=code)
        db.session.add(otp)
        db.session.commit()

        muvaffaqiyat = telegram_otp_yuborish(user.telegram_chat_id, code)

        if muvaffaqiyat:
            session['reset_username'] = username
            return redirect('/verify-otp')
        else:
            return redirect('/forgot-password?error=Telegram ga yuborishda xato! Token yoki Chat ID ni tekshiring.')

    return render_template('forgot_password.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_username' not in session:
        return redirect('/forgot-password')

    username = session['reset_username']

    if request.method == 'POST':
        entered_code = request.form['code'].strip()

        otp = OTPCode.query.filter_by(
            username=username,
            used=False
        ).order_by(OTPCode.created_at.desc()).first()

        if not otp:
            return redirect('/verify-otp?error=Kod topilmadi. Qayta so\'rang.')

        if not otp.is_valid():
            return redirect('/verify-otp?error=Kod muddati o\'tgan! Qayta so\'rang.')

        if otp.code != entered_code:
            return redirect('/verify-otp?error=Noto\'g\'ri kod! Qayta urinib ko\'ring.')

        otp.used = True
        db.session.commit()

        session['otp_verified'] = True
        return redirect('/reset-password')

    return render_template('verify_otp.html', username=username)

@app.route('/resend-otp')
def resend_otp():
    if 'reset_username' not in session:
        return redirect('/forgot-password')

    username = session['reset_username']
    user = User.query.filter_by(username=username).first()

    if not user or not user.telegram_chat_id:
        return redirect('/forgot-password')

    code = str(random.randint(100000, 999999))
    OTPCode.query.filter_by(username=username, used=False).delete()
    db.session.commit()

    otp = OTPCode(username=username, code=code)
    db.session.add(otp)
    db.session.commit()

    muvaffaqiyat = telegram_otp_yuborish(user.telegram_chat_id, code)

    if muvaffaqiyat:
        return redirect('/verify-otp?success=Yangi kod yuborildi!')
    else:
        return redirect('/verify-otp?error=Yuborishda xato!')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_username' not in session or not session.get('otp_verified'):
        return redirect('/forgot-password')

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            return redirect('/reset-password?error=Parollar mos kelmadi!')

        if len(new_password) < 6:
            return redirect('/reset-password?error=Parol kamida 6 ta belgi bo\'lishi kerak!')

        user = User.query.filter_by(username=session['reset_username']).first()
        user.set_password(new_password)
        db.session.commit()

        session.pop('reset_username', None)
        session.pop('otp_verified', None)

        return redirect('/?success=Parol muvaffaqiyatli yangilandi! Kiring.')

    return render_template('reset_password.html')

# =================== DASHBOARD ===================

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    expenses = Expense.query.filter_by(
        user_id=session['user_id']
    ).order_by(Expense.date.desc()).all()
    total = sum(e.amount for e in expenses)
    return render_template('dashboard.html', expenses=expenses, total=total)

@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        new_expense = Expense(
            amount=float(request.form['amount']),
            category=request.form['category'],
            description=request.form.get('description', ''),
            user_id=session['user_id']
        )
        db.session.add(new_expense)
        db.session.commit()
        return redirect('/dashboard')
    return render_template('add_expense.html')

@app.route('/delete/<int:expense_id>')
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect('/')
    expense = Expense.query.filter_by(
        id=expense_id, user_id=session['user_id']
    ).first()
    if expense:
        db.session.delete(expense)
        db.session.commit()
    return redirect('/dashboard')

# =================== ISHGA TUSHIRISH ===================

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)