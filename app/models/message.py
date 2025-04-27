# app/models/message.py

from datetime import datetime
from app import db

class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)

    # 🔁 Routing Info
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # 🔐 MTProto Encrypted Content
    encrypted_data = db.Column(db.LargeBinary, nullable=False)  # Encrypted payload (text + metadata)
    msg_key = db.Column(db.String(64), nullable=True)          # Middle 128 bits of SHA256
    auth_key_id = db.Column(db.String(64), nullable=True)      # SHA1(auth_key)[-8:]

    # 🔒 MTProto 2.0 Encryption Metadata
    salt = db.Column(db.String(64), nullable=True)              # Random salt for session
    session_id = db.Column(db.String(64), nullable=True)        # 64-bit session ID
    msg_id = db.Column(db.String(128), nullable=True)           # Message ID (timestamp-based)
    seq_no = db.Column(db.Integer, nullable=True)               # Sequence number for ordering

    # 📎 Media Handling
    file_path = db.Column(db.String(256), nullable=True)        # Path to encrypted file (optional)
    thumbnail_path = db.Column(db.String(256), nullable=True)   # Path to encrypted thumbnail (optional)
    media_type = db.Column(db.String(32), nullable=True)        # image, video, file, etc.
    original_filename = db.Column(db.String(128), nullable=True)

    # ✅ Status & Flags
    status = db.Column(db.String(16), default="sent")           # sent, delivered, read, failed
    retry_count = db.Column(db.Integer, default=0)              # For retry mechanisms

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    visible_to_sender = db.Column(db.Boolean, default=True)
    visible_to_receiver = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return (
            f"<Message {self.id} from {self.sender_id} to {self.receiver_id} "
            f"status={self.status} retry={self.retry_count}>"
        )