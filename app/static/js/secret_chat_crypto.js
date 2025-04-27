// Converts BigInt (DH shared key) to an AES key
async function deriveAESKey(sharedSecret) {
    const sharedArray = bigIntToUint8Array(sharedSecret);  // Convert BigInt to Uint8Array

    const hash = await crypto.subtle.digest('SHA-256', sharedArray);  // SHA-256 hash → 256-bit key
    const aesKey = await crypto.subtle.importKey(
        'raw',
        hash,
        { name: 'AES-GCM' },
        false,
        ['encrypt', 'decrypt']
    );

    // 💡 Log AES key (256-bit)
    const keyHex = Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, '0')).join('');
    console.log(`🔑 Derived AES key (256-bit): ${keyHex} (length: ${hash.byteLength * 8} bits)`);

    return aesKey;
}

// Encrypt message using AES-GCM
async function encryptMessageWithAES(sharedSecret, plaintext) {
    const aesKey = await deriveAESKey(sharedSecret);
    const iv = crypto.getRandomValues(new Uint8Array(12)); // 96-bit IV for GCM
    const encodedText = new TextEncoder().encode(plaintext);

    const ciphertext = await crypto.subtle.encrypt(
        {
            name: 'AES-GCM',
            iv: iv
        },
        aesKey,
        encodedText
    );

    // Combine IV and ciphertext
    const ivBase64 = arrayBufferToBase64(iv);
    const ciphertextBase64 = arrayBufferToBase64(ciphertext);
    console.log(`📦 Encrypted message - IV: ${ivBase64}, Ciphertext: ${ciphertextBase64}`);
    return ivBase64 + ":" + ciphertextBase64;
}

// Decrypt message using AES-GCM
async function decryptMessageWithAES(sharedSecret, combinedCiphertext) {
    // Convert bytes back to string if needed
    if (combinedCiphertext instanceof ArrayBuffer) {
        combinedCiphertext = new TextDecoder().decode(combinedCiphertext);
    }

    const [ivBase64, ciphertextBase64] = combinedCiphertext.split(":");
    const iv = base64ToArrayBuffer(ivBase64);
    const ciphertext = base64ToArrayBuffer(ciphertextBase64);

    const aesKey = await deriveAESKey(sharedSecret);
    const decrypted = await crypto.subtle.decrypt(
        {
            name: 'AES-GCM',
            iv: iv
        },
        aesKey,
        ciphertext
    );

    const plainText = new TextDecoder().decode(decrypted);
    console.log(`🔓 Decrypted message: ${plainText}`);
    return plainText;
}

// Convert BigInt to Uint8Array
function bigIntToUint8Array(bigInt) {
    let hex = bigInt.toString(16);
    if (hex.length % 2) hex = '0' + hex;  // Ensure even-length hex
    const len = hex.length / 2;
    const u8 = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        u8[i] = parseInt(hex.substr(i * 2, 2), 16);
    }
    return u8;  // Return Uint8Array directly
}

// Base64 utility functions
function arrayBufferToBase64(buffer) {
    return btoa(String.fromCharCode(...new Uint8Array(buffer)));
}

function base64ToArrayBuffer(base64) {
    const binary = atob(base64);
    const len = binary.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
}