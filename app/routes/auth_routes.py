from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from app import db, mail
from app.models.user import User
from app.services.otp_service import send_otp_email, send_otp_sms, generate_otp
from app.services.encryption_service import encrypt_message, decrypt_message
from datetime import datetime, timedelta
from flask_mail import Message as MailMessage

auth_bp = Blueprint("auth", __name__)

# -------------------------------
# 📝 Register User
# -------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    phone = data.get("phone")
    password = data.get("password")

    if not password or not (email or phone or username):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter((User.email == email) | (User.phone == phone) | (User.username == username)).first():
        return jsonify({"error": "User already exists"}), 400

    user = User(username=username, email=email, phone=phone)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201


# -------------------------------
# 🔐 Login User
# -------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    login_id = data.get("login_id")
    password = data.get("password")

    user = User.query.filter(
        (User.email == login_id) |
        (User.phone == login_id) |
        (User.username == login_id)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    user.last_login = datetime.utcnow()
    db.session.commit()

    session["user_id"] = user.id
    session["username"] = user.username

    return jsonify({
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username
    })


# -------------------------------
# 🚪 Logout User
# -------------------------------
@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("general.index"))


# -------------------------------
# 📲 Forgot Password (Send OTP)
# -------------------------------
@auth_bp.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.json
    recipient = data.get("recipient")

    user = User.query.filter(
        (User.email == recipient) |
        (User.phone == recipient)
    ).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    otp_code = generate_otp()
    expiry = datetime.utcnow() + timedelta(minutes=10)

    user.otp_code = otp_code
    user.otp_expiry = expiry
    db.session.commit()

    if "@" in recipient:
        send_otp_email(recipient, otp_code)
    else:
        send_otp_sms(recipient, otp_code)

    return jsonify({"message": "OTP sent"})


# -------------------------------
# ✅ Verify OTP & Reset Password
# -------------------------------
@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.json
    recipient = data.get("recipient")
    otp = data.get("otp")
    new_password = data.get("new_password")

    user = User.query.filter(
        (User.email == recipient) |
        (User.phone == recipient)
    ).first()

    if not user or user.otp_code != otp:
        return jsonify({"error": "Invalid OTP"}), 401

    if datetime.utcnow() > user.otp_expiry:
        return jsonify({"error": "OTP expired"}), 403

    user.set_password(new_password)
    user.otp_code = None
    user.otp_expiry = None
    user.is_verified = True
    db.session.commit()

    return jsonify({"message": "Password reset successful"})


# -------------------------------
# 🔐 Encrypt and Return MTProto Encrypted Payload
# -------------------------------
@auth_bp.route("/send-message", methods=["POST"])
def send_message():
    data = request.get_json()
    user_id = data.get("user_id")
    recipient_id = data.get("recipient_id")
    plaintext_message = data.get("message")

    sender_user = User.query.filter_by(id=user_id).first()
    recipient_user = User.query.filter_by(id=recipient_id).first()

    if not sender_user or not recipient_user:
        return jsonify({"error": "User or recipient not found"}), 404

    # Pass both sender and recipient to encryption
    encrypted_data, msg_key, auth_key_id, salt, session_id, msg_id, seq_no = encrypt_message(
        sender_user, recipient_user, plaintext_message
    )

    return jsonify({
        "message": "Encrypted message generated",
        "payload": {
            "message": encrypted_data.hex(),
            "msg_key": msg_key,
            "auth_key_id": auth_key_id,
            "salt": salt,
            "session_id": session_id,
            "msg_id": msg_id,
            "seq_no": seq_no
        }
    }), 201


# -------------------------------
# 🔓 Decrypt MTProto Message
# -------------------------------
@auth_bp.route("/decrypt-message", methods=["POST"])
def decrypt_msg():
    data = request.get_json()
    encrypted_message_hex = data.get("encrypted_message")
    msg_key = data.get("msg_key")
    auth_key_id = data.get("auth_key_id")

    encrypted_message = bytes.fromhex(encrypted_message_hex)
    decrypted_message = decrypt_message(encrypted_message, msg_key, auth_key_id)

    if "error" in decrypted_message:
        return jsonify(decrypted_message), 400

    return jsonify({"decrypted_message": decrypted_message.get("text")}), 200