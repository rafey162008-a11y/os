import os
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """Base application configuration."""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-me'
    FLASK_DEBUG = os.environ.get('FLASK_DEBUG', '1') == '1'

    # Database
    # Defaults to a local SQLite file. Set DATABASE_URL in .env to use
    # PostgreSQL instead, e.g. postgresql://user:pass@localhost:5432/dbname
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'online_shopping.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Engine options: SQLite needs check_same_thread disabled for Flask's
    # threaded dev server; PostgreSQL uses connection pooling settings.
    if SQLALCHEMY_DATABASE_URI.startswith('sqlite'):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'connect_args': {'check_same_thread': False},
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 280,
        }

    # Uploads
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico'}

    # Session
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 days
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 30  # 30 days

    # Pagination
    PRODUCTS_PER_PAGE = 12
    ADMIN_PER_PAGE = 15

    # Store settings
    STORE_NAME = 'ShopSphere'
    STORE_CURRENCY = '$'
    DEFAULT_TAX_RATE = 0.0  # configured in Settings table
    DEFAULT_SHIPPING_FLAT = 5.0
    FREE_SHIPPING_THRESHOLD = 100.0
    FREE_SHIPPING_ACTIVE = True

    # Payment (placeholders - never hardcode real keys)
    PAYMENT_API_KEY = os.environ.get('PAYMENT_API_KEY') or ''

    # Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or ''
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or ''
