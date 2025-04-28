from flask import Blueprint, request, jsonify
from flask_socketio import emit, join_room, leave_room, disconnect
from app import db, socketio
from app.models.user import User
from app.models.message import Message
from app.services.encryption_service import encrypt_message, decrypt_message
from datetime import datetime
import logging

chat_bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)

connected_users = {}

@chat_bp.route("/messages/<int:user_id>", methods=["GET"])
def get_messages(user_id):
    messages = Message.query.filter(
        (Message.sender_id == user_id) | (Message.receiver_id == user_id)
    ).order_by(Message.timestamp.asc()).all()

    results = []
    for msg in messages:
        if msg.auth_key_id:
            decrypted = decrypt_message(msg.encrypted_data, msg.msg_key, msg.auth_key_id)
            text = decrypted.get("text")
        else:
            text = msg.encrypted_data  # For secret chats (E2EE)
        results.append({
            "id": msg.id,
            "from": msg.sender_id,
            "to": msg.receiver_id,
            "text": text,
            "media_type": msg.media_type,
            "timestamp": msg.timestamp.isoformat(),
            "status": msg.status,
            "file": msg.file_path,
            "thumbnail": msg.thumbnail_path
        })
    return jsonify(results)

@socketio.on("exchange_public_key")
def handle_public_key_exchange(data):
    sender_id = data.get("sender_id")
    receiver_id = data.get("receiver_id")
    public_key = data.get("public_key")

    emit("receive_public_key", {
        "sender_id": sender_id,
        "public_key": public_key
    }, room=f"user_{receiver_id}")

@socketio.on("send_message")
def handle_send_message(data):
    sender_id = data.get("sender_id")
    receiver_id = data.get("receiver_id")
    text = data.get("text")
    chat_mode = data.get("chat_mode", "cloud")

    sender = User.query.get(sender_id)
    receiver = User.query.get(receiver_id)
    if not sender or not receiver:
        emit("error", {"message": "User not found"})
        return

    receiver_room = f"user_{receiver.id}"
    sender_room = f"user_{sender.id}"

    active_sids = socketio.server.manager.rooms.get("/", {}).get(receiver_room, set())

    # 🔐 Secret Chat Logic (unchanged)
    if chat_mode == "secret":
        print(f"\n📤 [Secret Chat] Relaying encrypted message from '{sender.username}' to '{receiver.username}'")
        print(f"🔒 [Secret Chat] Server cannot decrypt this message.\n")

        encrypted_text = text.encode('utf-8')

        message = Message(
            sender_id=sender.id,
            receiver_id=receiver.id,
            encrypted_data=encrypted_text,
            msg_key=None,
            auth_key_id=b'secretchat',
            session_id=data.get("session_id"),
            salt=data.get("salt"),
            msg_id=b'secretchat',
            seq_no=None,
            status="sent"
        )
        db.session.add(message)
        db.session.commit()

        # Emit to receiver (if online)
        if active_sids:
            emit("receive_message", {
                "id": message.id,
                "from": sender.id,
                "to": receiver.id,
                "text": message.encrypted_data.decode('utf-8'),
                "timestamp": message.timestamp.isoformat(),
                "status": "✔",
                "chat_mode": "secret"
            }, room=receiver_room)
            message.status = "delivered"
            db.session.commit()

        # Emit to sender (always)
        emit("receive_message", {
            "id": message.id,
            "from": sender.id,
            "to": receiver.id,
            "text": message.encrypted_data.decode('utf-8'),
            "timestamp": message.timestamp.isoformat(),
            "status": message.status,
            "chat_mode": "secret"
        }, room=sender_room)

    # ☁️ Cloud Chat Logic
    else:
        print(f"\n📨 [Cloud Chat] Message sent from '{sender.username}' to '{receiver.username}'")

        # Encrypt message (server-side encryption)
        encrypted_blob, msg_key, auth_key_id, salt, session_id, msg_id, seq_no = encrypt_message(sender, receiver, text)
        logger.info(f"[ENCRYPT] User '{sender.username}' sent message to '{receiver.username}'")

        message = Message(
            sender_id=sender.id,
            receiver_id=receiver.id,
            encrypted_data=encrypted_blob,
            msg_key=msg_key,
            auth_key_id=auth_key_id,
            session_id=session_id,
            salt=salt,
            msg_id=msg_id,
            seq_no=seq_no,
            status="sent"
        )
        db.session.add(message)
        db.session.commit()

        # Decrypt message for frontend (plaintext)
        decrypted = decrypt_message(encrypted_blob, msg_key, auth_key_id)

        # Log decrypted message for Cloud Chat
        print(f"🔓 [Cloud Chat] Decrypted message: \"{decrypted.get('text')}\"\n")

        # Emit to receiver (if online)
        if active_sids:
            emit("receive_message", {
                "id": message.id,
                "from": sender.id,
                "to": receiver.id,
                "text": decrypted.get("text"),
                "timestamp": message.timestamp.isoformat(),
                "status": "✔",
                "chat_mode": "cloud"
            }, room=receiver_room)
            message.status = "delivered"
            db.session.commit()

        # Emit to sender (always)
        emit("receive_message", {
            "id": message.id,
            "from": sender.id,
            "to": receiver.id,
            "text": decrypted.get("text"),
            "timestamp": message.timestamp.isoformat(),
            "status": message.status,
            "chat_mode": "cloud"
        }, room=sender_room)

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

@chat_bp.route("/contacts/<int:user_id>")
def get_contacts(user_id):
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

    all_users = User.query.filter(User.id != user_id).all()
    for u in all_users:
        if u.id not in seen:
            ordered_contacts.append({
                "id": u.id,
                "username": u.username or u.email or u.phone
            })

    return jsonify(ordered_contacts)

@socketio.on("join")
def handle_join(data):
    user_id = data.get("user_id")
    room = f"user_{user_id}"
    sid = request.sid

    # ✅ Add socket ID to connected_users
    if user_id not in connected_users:
        connected_users[user_id] = set()
    connected_users[user_id].add(sid)

    # ✅ Only mark the user as online the FIRST time
    if len(connected_users[user_id]) == 1:
        user = User.query.get(user_id)
        if user:
            user.is_online = True
            user.last_seen = datetime.utcnow()
            db.session.commit()

            print(f"🔔 User '{user.username}' came ONLINE. Delivering stored messages...")

            pending_messages = Message.query.filter_by(receiver_id=user_id, status="sent").all()
            for msg in pending_messages:
                chat_mode = "secret" if msg.auth_key_id == b'secretchat' else "cloud"
                emit("receive_message", {
                    "id": msg.id,
                    "from": msg.sender_id,
                    "to": msg.receiver_id,
                    "text": msg.encrypted_data.decode('utf-8') if chat_mode == "secret" else decrypt_message(msg.encrypted_data, msg.msg_key, msg.auth_key_id).get("text"),
                    "timestamp": msg.timestamp.isoformat(),
                    "status": "✔",
                    "chat_mode": chat_mode
                }, room=room)
                msg.status = "delivered"
            db.session.commit()

    join_room(room)

@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    for user_id, sids in connected_users.items():
        if sid in sids:
            sids.remove(sid)
            if not sids:
                user = User.query.get(user_id)
                if user:
                    user.is_online = False
                    user.last_seen = datetime.utcnow()
                    db.session.commit()
                    print(f"🔌 User '{user.username}' went OFFLINE.")
            break

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
        db.session.delete(message)
    else:
        if message.sender_id == user_id:
            message.visible_to_sender = False
        elif message.receiver_id == user_id:
            message.visible_to_receiver = False

    db.session.commit()
    return jsonify({"success": True})

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