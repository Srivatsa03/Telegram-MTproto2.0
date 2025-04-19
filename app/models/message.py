# app/models/message.py

from datetime import datetime
from app import db

class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)

    # Message routing
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Core encrypted content
    encrypted_data = db.Column(db.LargeBinary, nullable=False)  # MTProto encrypted blob
    msg_key = db.Column(db.String(64), nullable=False)
    auth_key_id = db.Column(db.String(64), nullable=False)

    # MTProto metadata
    session_id = db.Column(db.String(64), nullable=True)
    msg_id = db.Column(db.String(128), nullable=True)
    salt = db.Column(db.String(64), nullable=True)
    seq_no = db.Column(db.Integer, nullable=True)

    # Optional file/media support
    file_path = db.Column(db.String(256), nullable=True)        # Encrypted file path
    thumbnail_path = db.Column(db.String(256), nullable=True)   # Encrypted preview/thumbnail
    media_type = db.Column(db.String(32), nullable=True)        # image, video, file, etc.
    original_filename = db.Column(db.String(128), nullable=True)

    # Message status
    status = db.Column(db.String(16), default="sent")  # sent, delivered, read, failed
    retry_count = db.Column(db.Integer, default=0)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    visible_to_sender = db.Column(db.Boolean, default=True)
    visible_to_receiver = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Message {self.id} from {self.sender_id} to {self.receiver_id}>"