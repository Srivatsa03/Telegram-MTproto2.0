import os
from Crypto.Util.number import getPrime, inverse, bytes_to_long, long_to_bytes
from hashlib import sha256, sha1

# DH Parameters from Telegram Spec (2048-bit MODP group)
DH_PRIME = int(
    "C71CAEB9C6B1DCE1D13D4BEB7C51FA30F6F3E499E8CEE0A1C2E3BDBDEF07A4BB"
    "6A98B733D0E8468C3F9E1B9B10A0F2C0EAB58CD7E5B29355D1E3DBF8D25E5B1D"
    "EE6BA6BC15BA9A1F21FE77B0387CFC3C9F8C0BFFFD5C14CC3DEAB2DCEB063683"
    "A14E1D8367D0E99C53937D93C60D8DF31A0EC0A7A93966FD858E12B4C63", 16
)

DH_GENERATOR = 3

# --------------------------------------
# 📥 Generate Server's DH Params
# --------------------------------------
def generate_server_dh_params():
    private = bytes_to_long(os.urandom(256)) % (DH_PRIME - 1)
    public = pow(DH_GENERATOR, private, DH_PRIME)
    return private, public

# --------------------------------------
# 📤 Compute Shared Auth Key
# --------------------------------------
def compute_auth_key(client_public, server_private):
    if not (1 < client_public < DH_PRIME - 1):
        raise ValueError("Invalid client public key")

    shared_secret = pow(client_public, server_private, DH_PRIME)
    auth_key = sha256(long_to_bytes(shared_secret)).digest()
    auth_key_id = sha1(auth_key).digest()[-8:]  # 64-bit key ID
    return auth_key, auth_key_id