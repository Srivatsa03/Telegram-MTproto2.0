from flask import Blueprint, request, jsonify
from flask_socketio import emit, join_room, disconnect
from app import db, socketio
from app.models.user import User
from app.models.message import Message
from app.services.encryption_service import encrypt_message, decrypt_message
from datetime import datetime

chat_bp = Blueprint("chat", __name__)

# -------------------------------
# 🧾 Fetch User's Chats (Inbox)
# -------------------------------
@chat_bp.route("/messages/<int:user_id>", methods=["GET"])
def get_messages(user_id):
    messages = Message.query.filter(
        (Message.sender_id == user_id) | (Message.receiver_id == user_id)
    ).order_by(Message.timestamp.asc()).all()

    results = []
    for msg in messages:
        decrypted = decrypt_message(msg.encrypted_data, msg.msg_key, msg.auth_key_id)
        results.append({
            "id": msg.id,
            "from": msg.sender_id,
            "to": msg.receiver_id,
            "text": decrypted.get("text"),
            "media_type": msg.media_type,
            "timestamp": msg.timestamp.isoformat(),
            "status": msg.status,
            "file": msg.file_path,
            "thumbnail": msg.thumbnail_path
        })

    return jsonify(results)

# -------------------------------
# 📡 Socket: Send Message
# -------------------------------
@socketio.on("send_message")
def handle_send_message(data):
    sender_id = data.get("sender_id")
    receiver_id = data.get("receiver_id")
    text = data.get("text")
    media = data.get("media")  # optional (base64/filepath)
    media_type = data.get("media_type")  # image, file, etc.

    sender = User.query.get(sender_id)
    receiver = User.query.get(receiver_id)

    if not sender or not receiver:
        emit("error", {"message": "User not found"})
        return

    encrypted_blob, msg_key, auth_key_id = encrypt_message(sender, text)

    message = Message(
        sender_id=sender.id,
        receiver_id=receiver.id,
        encrypted_data=encrypted_blob,
        msg_key=msg_key,
        auth_key_id=auth_key_id,
        session_id=data.get("session_id"),
        salt=data.get("salt"),
        msg_id=data.get("msg_id"),
        seq_no=data.get("seq_no"),
        media_type=media_type,
        file_path=data.get("file_path"),
        thumbnail_path=data.get("thumbnail_path"),
        original_filename=data.get("filename"),
        status="sent"
    )

    db.session.add(message)
    db.session.commit()

    # Notify receiver in real time
    room = f"user_{receiver.id}"
    emit("receive_message", {
        "id": message.id,
        "from": sender.id,
        "to": receiver.id,
        "text": text,
        "timestamp": message.timestamp.isoformat(),
        "status": "✔"
    }, room=room)

    # Acknowledge sender (✔)
    emit("message_status", {
        "message_id": message.id,
        "status": "✔"
    }, room=f"user_{sender.id}")

# -------------------------------
# ✅ Socket: Message Read
# -------------------------------
@socketio.on("mark_read")
def mark_message_read(data):
    message_id = data.get("message_id")
    message = Message.query.get(message_id)
    if message and message.status != "read":
        message.status = "read"
        db.session.commit()

        emit("message_status", {
            "message_id": message.id,
            "status": "✅"
        }, room=f"user_{message.sender_id}")

# -------------------------------
# ✔✔ Socket: Message Delivered
# -------------------------------
@socketio.on("message_status")
def update_message_status(data):
    message_id = data.get("message_id")
    new_status = data.get("status")

    message = Message.query.get(message_id)
    if message and new_status and message.status != "read":
        message.status = new_status
        db.session.commit()

        emit("message_status", {
            "message_id": message.id,
            "status": new_status
        }, room=f"user_{message.sender_id}")

# -------------------------------
# 👥 Load Chat Contacts
# -------------------------------
@chat_bp.route("/contacts/<int:user_id>")
def get_contacts(user_id):
    from app.models.user import User

    messages = Message.query.filter(
        (Message.sender_id == user_id) | (Message.receiver_id == user_id)
    ).order_by(Message.timestamp.desc()).all()

    seen = set()
    ordered_contacts = []

    for msg in messages:
        other_id = msg.receiver_id if msg.sender_id == user_id else msg.sender_id
        if other_id != user_id and other_id not in seen:
            user = User.query.get(other_id)
            if user:
                ordered_contacts.append({
                    "id": user.id,
                    "username": user.username or user.email or user.phone
                })
                seen.add(other_id)

    # Now add the rest of users
    all_users = User.query.filter(User.id != user_id).all()
    for u in all_users:
        if u.id not in seen:
            ordered_contacts.append({
                "id": u.id,
                "username": u.username or u.email or u.phone
            })

    return jsonify(ordered_contacts)

# -------------------------------
# 🔌 Socket.IO Events
# -------------------------------
@socketio.on("join")
def handle_join(data):
    user_id = data.get("user_id")
    room = f"user_{user_id}"
    
    # Avoid joining the same room multiple times for the same user
    if request.sid not in socketio.server.manager.get_participants(room):
        print(f"User {user_id} joining room {room}.")
        join_room(room)
        
        user = User.query.get(user_id)
        if user:
            user.is_online = True
            user.last_seen = datetime.utcnow()
            db.session.commit()
            print(f"User {user.username} is now online.")
        else:
            print(f"User with ID {user_id} not found.")
    else:
        print(f"User {user_id} already connected. Skipping.")

@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    print(f"🔌 Socket {sid} disconnected")

# -------------------------------
# ✍️ Typing Indicator
# -------------------------------
@socketio.on("typing")
def handle_typing(data):
    sender = data.get("from")
    receiver = data.get("to")
    room = f"user_{receiver}"
    user = User.query.get(sender)

    if user:
        emit("typing", {
            "from": sender,
            "username": user.username or user.email or "Someone"
        }, room=room)

@socketio.on("connect")
def handle_connect():
    print("User connected")

# -------------------------------
# 🗑️ Delete Message
# -------------------------------
@chat_bp.route("/delete_message", methods=["POST"])
def delete_message():
    data = request.json
    message_id = data.get("message_id")
    user_id = data.get("user_id")
    delete_for_all = data.get("delete_for_all", False)

    message = Message.query.get(message_id)
    if not message:
        return jsonify({"success": False, "message": "Message not found"})

    if delete_for_all:
        db.session.delete(message)  # Deletes message completely for everyone
    else:
        if message.sender_id == user_id:
            message.visible_to_sender = False
        elif message.receiver_id == user_id:
            message.visible_to_receiver = False

    db.session.commit()
    return jsonify({"success": True})

# -------------------------------
# ✅ Clear Chat - Delete All Messages
# -------------------------------
@chat_bp.route("/delete_chat/<int:user_id>/<int:with_user_id>", methods=["POST"])
def delete_chat(user_id, with_user_id):
    messages = Message.query.filter(
        ((Message.sender_id == user_id) & (Message.receiver_id == with_user_id)) |
        ((Message.receiver_id == user_id) & (Message.sender_id == with_user_id))
    ).all()

    for msg in messages:
        if msg.sender_id == user_id:
            msg.visible_to_sender = False
        elif msg.receiver_id == user_id:
            msg.visible_to_receiver = False

    db.session.commit()
    return jsonify({"success": True})