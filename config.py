import os

class Config:
    SECRET_KEY    = os.environ.get('SECRET_KEY', 'mening_maxfiy_kalitim')
    db_url        = os.environ.get('DATABASE_URL', 'sqlite:///xarajatlar.db')
    SQLALCHEMY_DATABASE_URI = (
        db_url.replace('postgres://', 'postgresql://')
        if db_url.startswith('postgres://') else db_url
    )
    BOT_TOKEN     = os.environ.get('BOT_TOKEN', '')
    GROQ_API_KEY  = os.environ.get('GROQ_API_KEY', '')
    SECRET_WORD   = os.environ.get('SECRET_WORD', 'Yordamchim qanisan?')
    WEBAPP_URL    = os.environ.get('WEBAPP_URL', 'https://toy8088.uz')