import os
import json
import time
from hashlib import sha256
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import logging
import base64
from datetime import datetime, timedelta


def get_user_logger(username, retention_days=7):
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Auto-delete old log files
    now = time.time()
    for filename in os.listdir(logs_dir):
        file_path = os.path.join(logs_dir, filename)
        if filename.endswith(".log") and os.path.isfile(file_path):
            file_mtime = os.path.getmtime(file_path)
            if now - file_mtime > retention_days * 86400:
                os.remove(file_path)

    log_file = os.path.join(logs_dir, f"{username}.log")
    logger_name = f"MTProtoLogger_{username}"
    logger = logging.getLogger(logger_name)

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


def aes_ige_encrypt(plaintext, key, iv, logger):
    logger.info("Encrypting with AES-IGE...")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(plaintext, AES.block_size))
    logger.debug(f"Encrypted data: {encrypted.hex()}")
    return encrypted


def aes_ige_decrypt(ciphertext, key, iv, logger):
    logger.info("Decrypting with AES-IGE...")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
    logger.debug(f"Decrypted data: {decrypted.hex()}")
    return decrypted


def derive_aes_key_iv(auth_key, msg_key, logger):
    logger.info("Deriving AES key and IV...")
    sha_a = sha256(msg_key + auth_key[0:36]).digest()
    sha_b = sha256(auth_key[40:76] + msg_key).digest()

    aes_key = sha_a[0:8] + sha_b[8:24] + sha_a[24:32]
    aes_iv = sha_b[0:8] + sha_a[8:24] + sha_b[24:32]
    logger.debug(f"AES key: {aes_key.hex()}")
    logger.debug(f"AES IV: {aes_iv.hex()}")
    return aes_key[:32], aes_iv[:16]


def generate_auth_key(logger):
    logger.info("Generating auth key using Diffie-Hellman (simulated)...")
    auth_key = get_random_bytes(256)
    logger.debug(f"Generated Auth Key: {auth_key.hex()}")
    return auth_key


def encrypt_message(sender_user, recipient_user, plaintext_str):
    sender = sender_user.username or sender_user.email or sender_user.phone
    recipient = recipient_user.username or recipient_user.email or recipient_user.phone
    logger = get_user_logger(sender)

    logger.info("===== MTProto ENCRYPTION FLOW START =====")
    logger.info(f"\U0001f4e4 User '{sender}' is sending a message to '{recipient}'")

    if not sender_user.auth_key:
        sender_user.auth_key = generate_auth_key(logger)
        sender_user.auth_key_id = sha256(sender_user.auth_key).hexdigest()

    salt_bytes = get_random_bytes(8)
    session_id_bytes = get_random_bytes(8)
    msg_id = int(time.time() * 1000)
    seq_no = int.from_bytes(get_random_bytes(4), byteorder='big')

    payload_dict = {
        "text": plaintext_str,
        "time": int(time.time()),
        "msg_id": msg_id,
        "seq_no": seq_no,
        "sender_id": sender_user.id,
        "recipient_id": recipient_user.id
    }
    payload = json.dumps(payload_dict).encode()

    to_encrypt = salt_bytes + session_id_bytes + payload
    temp_data = sender_user.auth_key[:32] + to_encrypt
    msg_key_full = sha256(temp_data).digest()
    msg_key = msg_key_full[8:24]

    aes_key, aes_iv = derive_aes_key_iv(sender_user.auth_key, msg_key, logger)
    encrypted_data = aes_ige_encrypt(to_encrypt, aes_key, aes_iv, logger)

    logger.debug(f"Auth Key ID         : {sender_user.auth_key_id}")
    logger.debug(f"Salt (hex)          : {salt_bytes.hex()}")
    logger.debug(f"Session ID (hex)    : {session_id_bytes.hex()}")
    logger.debug(f"Msg ID              : {msg_id}")
    logger.debug(f"Seq No              : {seq_no}")
    logger.debug("Payload JSON        :\n" + json.dumps(payload_dict, indent=4))
    logger.debug("Encrypted (base64)  : " + base64.b64encode(encrypted_data).decode())

    logger.info("===== MTProto ENCRYPTION FLOW END =====\n")

    return (
        encrypted_data,
        msg_key.hex(),
        sender_user.auth_key_id,
        salt_bytes.hex(),
        session_id_bytes.hex(),
        str(msg_id),
        seq_no
    )


def decrypt_message(encrypted_blob, msg_key_hex, auth_key_id):
    from app.models.user import User
    from app import db

    user = User.query.filter_by(auth_key_id=auth_key_id).first()
    if not user or not user.auth_key:
        return {"error": "Auth key not found"}

    msg_key = bytes.fromhex(msg_key_hex)
    temp_logger = get_user_logger("temp_debug")
    aes_key, aes_iv = derive_aes_key_iv(user.auth_key, msg_key, temp_logger)

    try:
        decrypted = aes_ige_decrypt(encrypted_blob, aes_key, aes_iv, temp_logger)
        salt = decrypted[0:8]
        session_id = decrypted[8:16]
        payload = decrypted[16:]

        payload_json = json.loads(payload.decode())

        recipient_id = payload_json.get("recipient_id")
        recipient = User.query.get(recipient_id)

        if recipient:
            recipient_name = recipient.username or recipient.email or recipient.phone
            logger = get_user_logger(recipient_name)
        else:
            logger = temp_logger

        logger.info("===== MTProto DECRYPTION FLOW START =====")
        logger.info(f"\U0001f4e5 User '{recipient_name}' is receiving a message...")
        logger.debug(f"Encrypted blob length: {len(encrypted_blob)} bytes")
        logger.debug(f"Encrypted blob (hex)  : {encrypted_blob.hex()}")

        logger.debug(f"Derived AES Key     : {aes_key.hex()}")
        logger.debug(f"Derived AES IV      : {aes_iv.hex()}")
        logger.info("Decrypting with AES-IGE...")
        logger.debug(f"Decrypted data: {decrypted.hex()}")
        logger.debug(f"Salt (hex)          : {salt.hex()}")
        logger.debug(f"Session ID (hex)    : {session_id.hex()}")
        logger.debug("Payload JSON        :\n" + json.dumps(payload_json, indent=4))
        logger.info("===== MTProto DECRYPTION FLOW END =====\n")

        return payload_json

    except Exception as e:
        temp_logger.error("❌ Padding error: likely wrong AES key/IV or corrupted ciphertext.")
        temp_logger.error("[DECRYPTION ERROR]", exc_info=True)
        return {"error": "Decryption failed"}
