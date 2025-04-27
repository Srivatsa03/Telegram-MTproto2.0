// secret_chat_dh.js

// Telegram's DH parameters (2048-bit prime `p` and generator `g`)
const g = 2n;
const p = BigInt('0x' + 
    "C71CAEB9C6B1A12361C23A45B56B0C7C" + 
    "182B0DB4F6A1B3E084BCA3A8A38F3B39" + 
    "84D21C1D0DF5A9E6D9A52BFA3F6E3AB1" + 
    "CFCF6A8BE1A29F11C77F8EE3F9AE0727" + 
    "0219DC29C34F35F0B8A2AC0BE0A149C5" + 
    "F9F29F2D31A9B46C2F418B59B3F7E47B" + 
    "CAF0300D9BEE833BBD38A6800C8A0BF8" + 
    "10E6A96F1D1BFAFAB1313F8F2ECFB6FA" + 
    "C18A06E3"
  );

// Generate private key (random 256-bit number)
function generatePrivateKey() {
    const array = new Uint8Array(32);
    window.crypto.getRandomValues(array);
    const privateKey = BigInt('0x' + Array.from(array).map(b => b.toString(16).padStart(2, '0')).join(''));

    // ✅ Log after defining privateKey
    console.log("🔑 Generated DH private key (256-bit):", privateKey.toString(16));
    return privateKey;
}

// Modular exponentiation (base^exponent % modulus)
function modPow(base, exponent, modulus) {
    let result = 1n;
    base = base % modulus;
    while (exponent > 0) {
        if (exponent % 2n === 1n) {
            result = (result * base) % modulus;
        }
        exponent = exponent / 2n;
        base = (base * base) % modulus;
    }
    return result;
}

// Export public key
function computePublicKey(privateKey) {
    const publicKey = modPow(g, privateKey, p);
    console.log("📤 Computed DH public key:", publicKey.toString(16));
    return publicKey;
}

// Derive shared key from other client’s public key
function computeSharedKey(otherPublicKey, privateKey) {
    const sharedSecret = modPow(otherPublicKey, privateKey, p);
    console.log("🤝 Computed shared secret (auth_key):", sharedSecret.toString(16));
    return sharedSecret;
}

// Expose functions globally for chat.js
window.generatePrivateKey = generatePrivateKey;
window.computePublicKey = computePublicKey;
window.computeSharedKey = computeSharedKey;