# app/services/otp_service.py

import random
from flask_mail import Message
from app import mail
from twilio.rest import Client
from flask import current_app

# -------------------------------
# 🔢 OTP Generation
# -------------------------------
def generate_otp(length=6):
    return ''.join(random.choices("0123456789", k=length))


# -------------------------------
# 📧 Send OTP via Email
# -------------------------------
def send_otp_email(recipient_email, otp_code):
    try:
        sender_email = current_app.config.get("MAIL_DEFAULT_SENDER") or current_app.config.get("MAIL_USERNAME")

        print(f"[DEBUG] Sending email from: {sender_email}")
        print(f"[DEBUG] OTP: {otp_code}")

        msg = Message(
            subject="Your OTP Code",
            sender=sender_email,
            recipients=[recipient_email],
            body=f"Your OTP code is: {otp_code}. It expires in 10 minutes."
        )
        mail.send(msg)
        print("[✅] Email sent successfully.")

        return "Email sent"  # ✅ RETURN value for testing

    except Exception as e:
        print(f"[EMAIL OTP ERROR] {str(e)}")
        return None  # Optional: helps test failures cleanly


# -------------------------------
# 📲 Send OTP via SMS (Twilio)
# -------------------------------
def send_otp_sms(phone_number, otp_code):
    try:
        twilio_sid = current_app.config["TWILIO_ACCOUNT_SID"]
        twilio_token = current_app.config["TWILIO_AUTH_TOKEN"]
        twilio_from = current_app.config["TWILIO_PHONE_NUMBER"]

        client = Client(twilio_sid, twilio_token)
        message = client.messages.create(
            body=f"Your OTP code is: {otp_code}. It expires in 10 minutes.",
            from_=twilio_from,
            to=phone_number
        )
    except Exception as e:
        print(f"[SMS OTP ERROR] {str(e)}")