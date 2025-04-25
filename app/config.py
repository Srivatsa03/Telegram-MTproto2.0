import os
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

class Config:
    # Security
    
    SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-dev-key") 
    # SQLAlchemy Database URI
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///../instance/app.db")  # Default to SQLite if DATABASE_URL is not set
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email OTP Configuration (SMTP)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")  # Gmail username (email)
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")  # Gmail password or app-specific password
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "srivatsakamballa.sk@gmail.com")

    # Email Debugging (Convert to boolean)
    MAIL_DEBUG = os.environ.get("MAIL_DEBUG", "False").lower() in ["true", "1", "t", "y", "yes"]

    # Uploads Configuration
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads", "media")
    THUMBNAIL_FOLDER = os.path.join(os.getcwd(), "uploads", "thumbnails")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB file size limit

    # Session Configuration (for security)
    SESSION_COOKIE_SECURE = False  # Set to True in production when using HTTPS
    DEBUG = os.environ.get("DEBUG", True)  # Default to True for development

    # Optional Future Extensions
    # Add more configurations as needed, for example:
    # SESSION_COOKIE_NAME = "my_session"
    # FLASK_ADMIN = os.environ.get("FLASK_ADMIN", False)

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)  # Only show errors, suppress requests