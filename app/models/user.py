from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import logging

# Setup logger
logger = logging.getLogger("MTProtoLogger")
logger.setLevel(logging.DEBUG)

# Create a file handler to write the logs to a file
file_handler = logging.FileHandler("mtproto_log.txt")
file_handler.setLevel(logging.DEBUG)

# Create a console handler to display logs in the terminal
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Set formatter for both handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # Identity fields
    username = db.Column(db.String(80), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(15), unique=True, nullable=True)

    # Auth and login
    password_hash = db.Column(db.String(128), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # OTP management
    otp_code = db.Column(db.String(6), nullable=True)
    otp_expiry = db.Column(db.DateTime, nullable=True)

    # MTProto auth key (DH shared key)
    auth_key = db.Column(db.LargeBinary, nullable=True)  # To store the auth key
    auth_key_id = db.Column(db.String(64), nullable=True)  # To store the ID of the auth key

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    messages_sent = db.relationship("Message", backref="sender", lazy=True, foreign_keys='Message.sender_id')
    messages_received = db.relationship("Message", backref="receiver", lazy=True, foreign_keys='Message.receiver_id')

    # Password utilities
    def set_password(self, password):
        """Hash the password and store it"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the entered password matches the stored hash"""
        return check_password_hash(self.password_hash, password)

    # Auth key management utilities
    def set_auth_key(self, auth_key):
        """Set the user's MTProto auth key"""
        self.auth_key = auth_key
        self.auth_key_id = generate_password_hash(auth_key.hex())  # Generate a unique ID for the auth key
        logger.info(f"Auth key for user {self.id} set with ID {self.auth_key_id}.")

    def get_auth_key(self):
        """Get the user's MTProto auth key"""
        return self.auth_key

    def __repr__(self):
        return f"<User {self.username or self.email or self.phone}>"