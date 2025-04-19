# app/models/user.py

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import logging
import os
import hashlib

# -----------------------------
# 📋 Logger Setup
# -----------------------------
logger = logging.getLogger("MTProtoLogger")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("mtproto_log.txt")
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# -----------------------------
# 👤 User Model (MTProto Ready)
# -----------------------------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # Identity
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(15), unique=True, nullable=True)

    # Authentication
    password_hash = db.Column(db.String(128), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # OTP
    otp_code = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)

    # 🔐 MTProto 2.0 Encryption Fields
    auth_key = db.Column(db.LargeBinary, nullable=True)       # 256-byte session auth key
    auth_key_id = db.Column(db.String(64), nullable=True)     # SHA1(auth_key)[-8:]
    salt = db.Column(db.String(64), nullable=True)            # Optional user-level salt
    session_id = db.Column(db.String(64), nullable=True)      # Optional user-level session ID

    # Activity & Presence
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    messages_sent = db.relationship("Message", backref="sender", lazy=True, foreign_keys='Message.sender_id')
    messages_received = db.relationship("Message", backref="receiver", lazy=True, foreign_keys='Message.receiver_id')

    # -------------------------
    # 🔐 Password Utilities
    # -------------------------
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # -------------------------
    # 🔑 MTProto Auth Key Management
    # -------------------------
    def set_auth_key(self, auth_key):
        """
        Set the user's MTProto 2.0 auth key and related metadata.
        This should only be called during DH key exchange.
        """
        self.auth_key = auth_key
        self.auth_key_id = hashlib.sha1(auth_key).digest()[-8:].hex()  # Proper 64-bit ID from SHA1
        self.salt = os.urandom(8).hex()
        self.session_id = os.urandom(8).hex()
        db.session.commit()

        logger.info(
            f"[AuthKey] Set for User {self.id} | "
            f"auth_key_id={self.auth_key_id}, salt={self.salt}, session_id={self.session_id}"
        )

    def get_auth_key(self):
        return self.auth_key

    def __repr__(self):
        return f"<User {self.username or self.email or self.phone}>"