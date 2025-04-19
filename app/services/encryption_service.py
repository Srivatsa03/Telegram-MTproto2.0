import os
import json
import time
from hashlib import sha256, sha1
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
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

# -------------------------------
# 🔐 AES-256 in IGE Mode (CBC Demo)
# -------------------------------
def aes_ige_encrypt(plaintext, key, iv):
    logger.info("Encrypting with AES-IGE...")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(plaintext, AES.block_size))
    logger.debug(f"Encrypted data: {encrypted.hex()}")
    return encrypted

def aes_ige_decrypt(ciphertext, key, iv):
    logger.info("Decrypting with AES-IGE...")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
    logger.debug(f"Decrypted data: {decrypted.hex()}")
    return decrypted

# -------------------------------
# 🔍 SHA256 Middle 128 Bits
# -------------------------------
def sha256_middle_128(data: bytes):
    full = sha256(data).digest()
    return full[8:24]

# -------------------------------
# 🔑 Derive AES Key & IV
# -------------------------------
def derive_aes_key_iv(auth_key, msg_key):
    logger.info("Deriving AES key and IV...")
    sha_a = sha256(msg_key + auth_key[0:36]).digest()
    sha_b = sha256(auth_key[40:76] + msg_key).digest()

    aes_key = sha_a[0:8] + sha_b[8:24] + sha_a[24:32]
    aes_iv = sha_b[0:8] + sha_a[8:24] + sha_b[24:32]
    logger.debug(f"AES key: {aes_key.hex()}")
    logger.debug(f"AES IV: {aes_iv.hex()}")
    return aes_key[:32], aes_iv[:16]

# -------------------------------
# 🔑 Generate Auth Key using Diffie-Hellman
# -------------------------------
def generate_auth_key():
    logger.info("Generating auth key using Diffie-Hellman (simulated)...")
    # Placeholder: Implement Diffie-Hellman key generation logic here
    auth_key = get_random_bytes(256)
    logger.debug(f"Generated Auth Key: {auth_key.hex()}")
    return auth_key

# ----------------------------------
# 🔒 Encrypt Message (MTProto style)
# ----------------------------------
def encrypt_message(user, plaintext_str):
    logger.info("Encrypting message using MTProto 2.0...")

    if not user.auth_key:
        # Generate new 256-bit session key if not exists
        user.auth_key = generate_auth_key()
        user.auth_key_id = sha256(user.auth_key).hexdigest()

    plaintext_bytes = json.dumps({"text": plaintext_str}).encode()

    # Step 1: Compute msg_key (middle 128 bits of SHA256 of auth_key + plaintext)
    temp_data = user.auth_key[:32] + plaintext_bytes
    msg_key_full = sha256(temp_data).digest()
    msg_key = msg_key_full[8:24]
    logger.debug(f"Generated Msg Key: {msg_key.hex()}")

    # Step 2: Derive AES key & IV
    aes_key, aes_iv = derive_aes_key_iv(user.auth_key, msg_key)

    # Step 3: Encrypt
    encrypted_data = aes_ige_encrypt(plaintext_bytes, aes_key, aes_iv)

    logger.info("Message encryption complete.")
    return encrypted_data, msg_key.hex(), user.auth_key_id

# ----------------------------------
# 🔓 Decrypt Message
# ----------------------------------
def decrypt_message(encrypted_blob, msg_key_hex, auth_key_id):
    from app.models.user import User
    from app import db

    logger.info(f"Decrypting message with auth_key_id: {auth_key_id}...")
    user = User.query.filter_by(auth_key_id=auth_key_id).first()
    if not user or not user.auth_key:
        logger.error("Auth key not found.")
        return {"error": "Auth key not found"}

    msg_key = bytes.fromhex(msg_key_hex)

    # Derive AES key/IV again
    aes_key, aes_iv = derive_aes_key_iv(user.auth_key, msg_key)

    try:
        plaintext = aes_ige_decrypt(encrypted_blob, aes_key, aes_iv)
        logger.debug(f"Decrypted plaintext: {plaintext}")
        return json.loads(plaintext.decode())
    except Exception as e:
        logger.error(f"[DECRYPTION ERROR]: {str(e)}")
        return {"error": "Decryption failed"}