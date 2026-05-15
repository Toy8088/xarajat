from flask import Blueprint, render_template, request, redirect, session
from models import db, User, Expense, OTPCode
from telegram import send_otp
import random

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        if User.query.filter_by(username=username).first():
            return redirect('/register?error=Bu username band!')
        user = User(username=username, telegram_chat_id=request.form.get('telegram_chat_id') or None)
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        return redirect('/?success=Ro\'yxatdan o\'tdingiz!')
    return render_template('register.html')

@bp.route('/login', methods=['POST'])
def login():
    user = User.query.filter_by(username=request.form['username']).first()
    if user and user.check_password(request.form['password']):
        session['user_id'] = user.id
        session['username'] = user.username
        return redirect('/dashboard')
    return redirect('/?error=Login yoki parol xato!')

@bp.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    expenses = Expense.query.filter_by(user_id=session['user_id']).order_by(Expense.date.desc()).all()
    return render_template('dashboard.html', expenses=expenses, total=sum(e.amount for e in expenses))

@bp.route('/add', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect('/')
    if request.method == 'POST':
        db.session.add(Expense(
            amount=float(request.form['amount']),
            category=request.form['category'],
            description=request.form.get('description', ''),
            user_id=session['user_id']
        ))
        db.session.commit()
        return redirect('/dashboard')
    return render_template('add_expense.html')

@bp.route('/delete/<int:id>')
def delete_expense(id):
    if 'user_id' not in session:
        return redirect('/')
    expense = Expense.query.filter_by(id=id, user_id=session['user_id']).first()
    if expense:
        db.session.delete(expense)
        db.session.commit()
    return redirect('/dashboard')

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if not user:
            return redirect('/forgot-password?error=Foydalanuvchi topilmadi!')
        if not user.telegram_chat_id:
            return redirect('/forgot-password?error=Telegram bog\'lanmagan!')
        code = str(random.randint(100000, 999999))
        OTPCode.query.filter_by(username=user.username, used=False).delete()
        db.session.add(OTPCode(username=user.username, code=code))
        db.session.commit()
        if send_otp(user.telegram_chat_id, code):
            session['reset_username'] = user.username
            return redirect('/verify-otp')
        return redirect('/forgot-password?error=Telegram xato!')
    return render_template('forgot_password.html')

@bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reset_username' not in session:
        return redirect('/forgot-password')
    username = session['reset_username']
    if request.method == 'POST':
        otp = OTPCode.query.filter_by(username=username, used=False).order_by(OTPCode.created_at.desc()).first()
        if not otp or not otp.is_valid():
            return redirect('/verify-otp?error=Kod yaroqsiz!')
        if otp.code != request.form['code'].strip():
            return redirect('/verify-otp?error=Noto\'g\'ri kod!')
        otp.used = True
        db.session.commit()
        session['otp_verified'] = True
        return redirect('/reset-password')
    return render_template('verify_otp.html', username=username)

@bp.route('/resend-otp')
def resend_otp():
    if 'reset_username' not in session:
        return redirect('/forgot-password')
    user = User.query.filter_by(username=session['reset_username']).first()
    code = str(random.randint(100000, 999999))
    OTPCode.query.filter_by(username=user.username, used=False).delete()
    db.session.add(OTPCode(username=user.username, code=code))
    db.session.commit()
    if send_otp(user.telegram_chat_id, code):
        return redirect('/verify-otp?success=Yangi kod yuborildi!')
    return redirect('/verify-otp?error=Xato!')

@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_username' not in session or not session.get('otp_verified'):
        return redirect('/forgot-password')
    if request.method == 'POST':
        if request.form['new_password'] != request.form['confirm_password']:
            return redirect('/reset-password?error=Parollar mos kelmadi!')
        user = User.query.filter_by(username=session['reset_username']).first()
        user.set_password(request.form['new_password'])
        db.session.commit()
        session.pop('reset_username', None)
        session.pop('otp_verified', None)
        return redirect('/?success=Parol yangilandi!')
    return render_template('reset_password.html')
