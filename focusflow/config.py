import os


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'f04ea855c1e38c32165e2c81d97abda5')
    APP_BASE_URL = 'http://localhost:5000'
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///focusflow.db')

    # Email Configuration - FIXED THE ISSUE!
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'False') == 'True'  # Should be False for Gmail
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'joanouma48@gmail.com')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'ebkruluctoquogly')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'joanouma48@gmail.com')

    # Additional recommended settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False