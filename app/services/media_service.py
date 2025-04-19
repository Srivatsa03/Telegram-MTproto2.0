# app/services/media_service.py

import os
from werkzeug.utils import secure_filename
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from base64 import b64encode, b64decode
from app import db
from app.models.user import User
from app.services.encryption_service import derive_aes_key_iv
from PIL import Image
import magic

MEDIA_FOLDER = os.path.join(os.getcwd(), "uploads", "media")
THUMBNAIL_FOLDER = os.path.join(os.getcwd(), "uploads", "thumbnails")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "pdf", "docx", "txt", "zip"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------------------
# 🔒 Encrypt & Save Media File
# -------------------------------------
def encrypt_and_save_file(file, user):
    if not allowed_file(file.filename):
        return None, "Unsupported file type"

    # Generate file info
    filename = secure_filename(file.filename)
    file_path = os.path.join(MEDIA_FOLDER, filename)

    # Read content
    file_data = file.read()

    # Use user's auth key
    if not user.auth_key:
        return None, "Missing encryption key"

    msg_key = get_random_bytes(16)
    aes_key, aes_iv = derive_aes_key_iv(user.auth_key, msg_key)

    cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
    encrypted_data = cipher.encrypt(file_data.ljust((len(file_data) + 15) // 16 * 16, b"\0"))

    with open(file_path, "wb") as f:
        f.write(encrypted_data)

    return file_path, None


# -------------------------------------
# 🔓 Decrypt Media for Download
# -------------------------------------
def decrypt_file(file_path, user, msg_key_hex):
    if not os.path.exists(file_path):
        return None

    with open(file_path, "rb") as f:
        encrypted_data = f.read()

    msg_key = bytes.fromhex(msg_key_hex)
    aes_key, aes_iv = derive_aes_key_iv(user.auth_key, msg_key)

    cipher = AES.new(aes_key, AES.MODE_CBC, aes_iv)
    decrypted = cipher.decrypt(encrypted_data)

    return decrypted.rstrip(b"\0")


# -------------------------------------
# 📷 Generate Thumbnail (Images)
# -------------------------------------
def generate_thumbnail(image_file, size=(150, 150)):
    try:
        img = Image.open(image_file)
        img.thumbnail(size)
        thumb_path = os.path.join(
            THUMBNAIL_FOLDER, "thumb_" + secure_filename(image_file.filename)
        )
        img.save(thumb_path)
        return thumb_path
    except Exception as e:
        print(f"[Thumbnail Error]: {e}")
        return None


# -------------------------------------
# 📦 Detect File Type
# -------------------------------------
def detect_file_type(file_path):
    try:
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)
        return file_type
    except Exception as e:
        return "unknown"