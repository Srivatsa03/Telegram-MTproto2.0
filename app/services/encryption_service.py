import os
import json
import time
from hashlib import sha256, sha1
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import logging
import base64

logger = logging.getLogger("MTProtoLogger")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    file_handler = logging.FileHandler("mtproto_log.txt")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

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

def derive_aes_key_iv(auth_key, msg_key):
    logger.info("Deriving AES key and IV...")
    sha_a = sha256(msg_key + auth_key[0:36]).digest()
    sha_b = sha256(auth_key[40:76] + msg_key).digest()

    aes_key = sha_a[0:8] + sha_b[8:24] + sha_a[24:32]
    aes_iv = sha_b[0:8] + sha_a[8:24] + sha_b[24:32]
    logger.debug(f"AES key: {aes_key.hex()}")
    logger.debug(f"AES IV: {aes_iv.hex()}")
    return aes_key[:32], aes_iv[:16]

def generate_auth_key():
    logger.info("Generating auth key using Diffie-Hellman (simulated)...")
    auth_key = get_random_bytes(256)
    logger.debug(f"Generated Auth Key: {auth_key.hex()}")
    return auth_key

def encrypt_message(user, plaintext_str):
    logger.info("===== MTProto ENCRYPTION FLOW START =====")

    if not user.auth_key:
        user.auth_key = generate_auth_key()
        user.auth_key_id = sha256(user.auth_key).hexdigest()

    salt_bytes = get_random_bytes(8)
    session_id_bytes = get_random_bytes(8)
    msg_id = int(time.time() * 1000)
    seq_no = int.from_bytes(get_random_bytes(4), byteorder='big')

    payload_dict = {
        "text": plaintext_str,
        "time": int(time.time()),
        "msg_id": msg_id,
        "seq_no": seq_no
    }
    payload = json.dumps(payload_dict).encode()

    to_encrypt = salt_bytes + session_id_bytes + payload
    temp_data = user.auth_key[:32] + to_encrypt
    msg_key_full = sha256(temp_data).digest()
    msg_key = msg_key_full[8:24]

    aes_key, aes_iv = derive_aes_key_iv(user.auth_key, msg_key)
    encrypted_data = aes_ige_encrypt(to_encrypt, aes_key, aes_iv)

    logger.debug(f"Auth Key ID         : {user.auth_key_id}")
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
        user.auth_key_id,
        salt_bytes.hex(),
        session_id_bytes.hex(),
        str(msg_id),
        seq_no
    )

def decrypt_message(encrypted_blob, msg_key_hex, auth_key_id):
    from app.models.user import User
    from app import db

    logger.info("===== MTProto DECRYPTION FLOW START =====")
    logger.info(f"Decrypting message with auth_key_id: {auth_key_id}...")

    user = User.query.filter_by(auth_key_id=auth_key_id).first()
    if not user or not user.auth_key:
        logger.error("Auth key not found.")
        return {"error": "Auth key not found"}

    msg_key = bytes.fromhex(msg_key_hex)
    aes_key, aes_iv = derive_aes_key_iv(user.auth_key, msg_key)

    try:
        decrypted = aes_ige_decrypt(encrypted_blob, aes_key, aes_iv)
        salt = decrypted[0:8]
        session_id = decrypted[8:16]
        payload = decrypted[16:]

        payload_json = json.loads(payload.decode())

        logger.debug(f"Derived AES Key     : {aes_key.hex()}")
        logger.debug(f"Derived AES IV      : {aes_iv.hex()}")
        logger.debug(f"Salt (hex)          : {salt.hex()}")
        logger.debug(f"Session ID (hex)    : {session_id.hex()}")
        logger.debug("Payload JSON        :\n" + json.dumps(payload_json, indent=4))

        logger.info("===== MTProto DECRYPTION FLOW END =====\n")

        return payload_json

    except Exception as e:
        logger.error(f"[DECRYPTION ERROR]: {str(e)}")
        return {"error": "Decryption failed"}
