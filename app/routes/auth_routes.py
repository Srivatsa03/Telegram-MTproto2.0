from flask import Blueprint, request, jsonify
from app import db, mail
from app.models.user import User
from app.services.otp_service import send_otp_email, send_otp_sms, generate_otp
from app.services.encryption_service import encrypt_message, decrypt_message
from datetime import datetime, timedelta
from flask_mail import Message as MailMessage
from flask import session, redirect, url_for, request, render_template

auth_bp = Blueprint("auth", __name__)

# -------------------------------
# 📝 Register User
# -------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    # Expecting JSON data
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    phone = data.get("phone")
    password = data.get("password")

    # Validate inputs
    if not password or not (email or phone or username):
        return jsonify({"error": "Missing required fields"}), 400

    # Check if user already exists
    if User.query.filter((User.email == email) | (User.phone == phone) | (User.username == username)).first():
        return jsonify({"error": "User already exists"}), 400

    # Create user
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
    login_id = data.get("login_id")  # username, email, or phone
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

    return jsonify({
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username
    })


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
# 🔐 Send Encrypted Message
# -------------------------------
@auth_bp.route("/send-message", methods=["POST"])
def send_message():
    data = request.get_json()
    user_id = data.get("user_id")
    recipient_id = data.get("recipient_id")
    plaintext_message = data.get("message")

    # Fetch user and recipient
    user = User.query.filter_by(id=user_id).first()
    recipient = User.query.filter_by(id=recipient_id).first()

    if not user or not recipient:
        return jsonify({"error": "User or recipient not found"}), 404

    # Encrypt message
    encrypted_data, msg_key, auth_key_id = encrypt_message(user, plaintext_message)

    # Store encrypted message in database (you can adjust the model as necessary)
    encrypted_message = {
        "sender_id": user.id,
        "receiver_id": recipient.id,
        "message": encrypted_data.hex(),
        "msg_key": msg_key,
        "auth_key_id": auth_key_id,
        "timestamp": datetime.utcnow()
    }

    db.session.add(encrypted_message)
    db.session.commit()

    return jsonify({"message": "Encrypted message sent successfully"}), 201


# -------------------------------
# 🔓 Decrypt Message
# -------------------------------
@auth_bp.route("/decrypt-message", methods=["POST"])
def decrypt_msg():
    data = request.get_json()
    encrypted_message_hex = data.get("encrypted_message")
    msg_key = data.get("msg_key")
    auth_key_id = data.get("auth_key_id")

    encrypted_message = bytes.fromhex(encrypted_message_hex)

    # Decrypt the message
    decrypted_message = decrypt_message(encrypted_message, msg_key, auth_key_id)

    if "error" in decrypted_message:
        return jsonify(decrypted_message), 400

    return jsonify({"decrypted_message": decrypted_message["text"]}), 200