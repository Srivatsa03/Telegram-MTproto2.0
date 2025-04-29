from flask import Blueprint, render_template, jsonify
from datetime import datetime

general_bp = Blueprint("general", __name__)

@general_bp.route("/")
def index():
    return render_template("index.html", hide_navbar=True)

@general_bp.route("/login")
def login_page():
    return render_template("login.html")

@general_bp.route("/register")
def register_page():
    return render_template("register.html")

@general_bp.route("/forgot_password")
def forgot_password_page():
    return render_template("forgot_password.html")

@general_bp.route("/chat")
def chat_page():
    return render_template("chat.html")

# 👇 MOVE THIS IMPORT INSIDE THE FUNCTION
@general_bp.route("/users")
def list_users():
    from app.models.user import User  # <--- move it here to avoid circular import
    users = User.query.all()
    user_list = [{"id": u.id, "username": u.username or u.email or u.phone} for u in users]
    return jsonify(user_list)

@general_bp.route("/status/<int:user_id>")
def get_user_status(user_id):
    from app.models.user import User
    user = User.query.get(user_id)
    if not user:
        return jsonify({"status": "unknown"})

    if user.is_online:
        return jsonify({"status": "online"})
    
    # Show "last seen"
    delta = datetime.utcnow() - user.last_seen
    minutes = int(delta.total_seconds() // 60)
    last_seen = f"{minutes} min ago" if minutes > 0 else "just now"

    return jsonify({"status": f"last seen {last_seen}"})

@general_bp.route("/user_info/<int:user_id>")
def user_info(user_id):
    from app.models.user import User
    user = User.query.get(user_id)
    if user:
        return jsonify({"username": user.username or user.email or user.phone})
    else:
        return jsonify({"username": None})