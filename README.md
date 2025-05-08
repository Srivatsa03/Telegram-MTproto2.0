# 🔐 MTProto Secure Messenger

A Flask-based secure chat application inspired by Telegram’s MTProto 2.0 protocol.  
Supports **end-to-end encrypted secret chats** and **server-assisted cloud messaging**,  
with real-time delivery, file sharing, typing indicators, and message status updates.

> Designed for CS588 — Security and Privacy in Network Distributed Systems | Spring 2025  
> Author: Srivatsa Kambala

---

## Prerequisites
- Python 3.9 or above
- pip (Python package manager)
- Git (for cloning the repository)
- A Unix-like environment (macOS/Linux preferred for smoother setup)

---

## Installation Instructions
1. Clone the Repository
   ```bash
   git clone https://github.com/Srivatsa03/Telegram-MTproto2.0.git
   cd mtproto-messenger
   ```
2. Set Up Python Virtual Environment
   ```bash
   python3/-m venv venv
   source venv/bin/activate  # On windows use: venv/Scripts/activate
   ```
3. Install Python Dependencies
   ```bash
   pip install -r requirements.txt"
   ```
4. Initialize the Database
   ```bash
   flask db init # only once
   flask db migrate -m "Initial Migration"
   flask db upgrade
   ```
5. Run the Application
   ```bash
   flask run
   ```
6. Open your browser and visit : http://127.0.01.5000/

---

## UI Usage & Walkthrough

The web-based UI provides a clean and interactive experience for secure messaging. Here's how to navigate and use the interface:

#### Login / Registration
- Access the application at `http://127.0.0.1:5000/`
- Click on **Login** or **Register**
- Provide email/phone/username and password to authenticate

#### Chat Interface Overview
- **Sidebar**: Displays a list of users you can chat with
- **Chat Mode Dropdown**: Choose between **Cloud Chat** and **Secret Chat**
- **Chat Window**: Shows sent and received messages
- **Typing Field**: Type and send messages
- **File Attachment**: Send encrypted files/images via the upload button

#### Secret Chat Mode
- Select **Secret Chat** from the dropdown
- Click **Initiate Secret Chat** to begin a secure DH key exchange
- After successful exchange, messages are encrypted using AES-256 IGE
- Server cannot read or decrypt secret messages
- Messages sent while the recipient is offline are queued and decrypted once the user is back online and key is re-established

#### Visual Indicators
- Secret chats have a dark-themed background to differentiate them
- Message status shows:
  - `✔` Sent
  - `✔✔` Delivered
  - `✅` Read
- Chat bubbles are color-coded based on sender/receiver and mode (cloud/secret)

#### Real-time Features
- Typing indicators show when the other user is typing
- Message delivery and read status updates live
- Online/offline status is shown beside usernames
- Auto-scrolls to the latest message upon new message arrival

--- 

## Testing with Multiple Users

To simulate secure messaging between two users on the same machine:

1. **Start the Flask server**:
   ```bash
   flask run
   ```
2.	Open two separate browsers:
	-	Use Chrome and Firefox, or
	-	Use Chrome and Chrome Incognito mode
3.	In each browser:
	-	Navigate to http://localhost:5000
	-	Register a different user account
	-	Log in with both accounts in their respective browsers
4.	After logging in:
	-	Select another user from the chat list
	-	Choose Cloud Chat or Secret Chat from the dropdown
	-	Exchange messages to verify real-time delivery, status updates, and encryption

This setup helps you verify how the application handles messaging, encryption, and online/offline behavior between two distinct sessions.

--- 

### Logs & Debugging Information

- **Secret Chat Logs**:
  - When using **Secret Chat**, messages are encrypted end-to-end.
  - Therefore, **the server terminal will not print any decrypted message content**.
  - To view debug info (key generation, encryption steps, etc.), **open your browser's Developer Tools → Console**.
  - Right-click anywhere → Inspect → Console tab.

- **Cloud Chat Logs**:
  - Cloud Chat uses server-side encryption and decryption.
  - All encryption steps, message payloads, and delivery logs are saved in the `logs/` directory.
  - Each user has their own log file:
    ```
    logs/
      srivatsa.log
      jaideep.log
      temp_debug.log
    ```
  - These files contain AES-256-IGE encryption metadata such as:
    - salt
    - session_id
    - msg_key
    - decrypted message text
    - full encryption lifecycle
   
---

## API & Socket Events

This project integrates REST API endpoints and WebSocket (Socket.IO) events for real-time, secure communication.

---

#### 🔒 Authentication Routes (`/auth/`)
- `POST /auth/login` — Log in with username/email/phone and password
- `POST /auth/register` — Register a new user
- `POST /auth/forgot_password` — Initiate password reset (OTP-based)
- `POST /auth/reset_password` — Reset with OTP and new password
- `GET /auth/logout` — Ends the session

---

#### 📋 General Routes (`/`)
- `GET /` — Landing page
- `GET /chat` — Loads chat.html
- `GET /users` — Lists all users for dropdown selection
- `GET /status/<user_id>` — Returns online status or last seen time

---

#### 🗂 Message Routes (`/chat/`)
- `GET /chat/messages/<user_id>` — Returns chat history for a given user
- `POST /chat/delete_message` — Deletes a specific message
- `POST /chat/delete_chat/<user_id>/<with_user_id>` — Deletes full chat thread

---

##  WebSocket (Socket.IO) Events

- `join` — `{ user_id }`  
  Joins the user's private room. Used on page load.

- `send_message`  
  Sends a message. Payload varies by chat mode (`cloud` or `secret`):
  ```json
  {
    "sender_id": 1,
    "receiver_id": 2,
    "text": "encrypted or plain text",
    "chat_mode": "secret/cloud",
    "msg_id": "...",
    "salt": "...",
    "session_id": "...",
    "seq_no": 1,
    "timestamp": "2025-04-28T14:32:00Z"
  }
- `receive_message`  
  Triggered on both sender and recipient side. Contains the message payload:
  - For **Cloud Chat**, it includes the decrypted plaintext.
  - For **Secret Chat**, it includes the AES-encrypted string, which the recipient decrypts client-side.

- `message_status`  
  Acknowledges delivery or read receipt. Example:
  ```json
  {
    "message_id": 123,
    "status": "✔✔"
  }
- `mark_read`  
  Marks a message as **read** after it appears in the recipient’s chat window.  
  Example payload sent by the client:
  ```json
  {
    "message_id": 456
  }
  ```
  This updates the message status to ✅ and notifies the sender via message_status.
- `typing`
  Sends a real-time “User is typing…” signal to the other user.
  Triggered every time the input field changes (on input event).
  Example:
  ``` json
  {
    "from": 1,
    "to": 2,
  }
  ```
  The UI displays a subtle status like:
  ```
  Jaideep is typing...
  ```
- `exchange_public_key`
   Used to initiate Secret Chat. Sends the initiating client’s DH public key to the recipient:
   ```json
   {
  "sender_id": 1,
  "receiver_id": 2,
  "public_key": "12345678901234567890"
   }
   ```
- `receive_public_key`
Triggered when the recipient receives the DH public key.
Responds with their own public key, computes the shared secret, and enables Secret Chat encryption.

This event also:
   - Logs shared secret setup.
   - Displays a “Secret Chat Initiated” UI toast.
   - Queues/decrypts any pending messages.

---

### MTProto-like Encryption Parameters

In both Cloud and Secret Chats, messages are wrapped with essential metadata before encryption to simulate the MTProto structure:

- **Salt**: A random 64-bit value used to add entropy and prevent replay attacks.
- **Session ID**: A unique identifier generated per client session to separate message contexts.
- **Message ID (msg_id)**: A 64-bit identifier created using the current timestamp in milliseconds.
- **Sequence Number (seq_no)**: Incremented per message per user to track message ordering and detect duplicates.
- **Payload**: The full message object (in JSON form), which includes:
  - `text`: Actual message text
  - `time`: UNIX timestamp
  - `msg_id`: Message identifier
  - `seq_no`: Sender’s current sequence number
  - `sender_id` and `receiver_id`: User IDs

In Secret Chats, the entire payload is encrypted client-side using the shared secret key derived from the DH exchange. In Cloud Chats, this payload is encrypted server-side using a persistent auth key (AES-256-IGE).

---

## 🔐 Security & Encryption Model

This application strictly adheres to end-to-end encrypted messaging principles, closely inspired by Telegram’s MTProto protocol. It supports **two modes** of communication:

### Cloud Chat (MTProto-Inspired Server-Side Encryption)

- Messages are **encrypted on the client**, sent to the server, then decrypted on the recipient’s client.
- The server performs AES-256 encryption/decryption using keys derived from a session-specific `auth_key`.
- All message objects include:
  - `salt`, `session_id`, `msg_id`, `seq_no` (MTProto-style fields)
  - `msg_key` (SHA256-based integrity check)
- Encrypted using **AES-256 IGE** with custom KDF derivation per message.
- Enables server-side syncing and offline message delivery.

### Secret Chat (Client-to-Client End-to-End Encryption)

- **Diffie-Hellman key exchange** happens between the clients.
- Shared secret is used to encrypt/decrypt messages using AES-256 (MTProto-style structure).
- The server:
  - Never sees the plaintext.
  - Never sees or generates the session key.
  - Only acts as a **relay** for public keys and encrypted blobs.
- Messages sent while a recipient is offline are delivered later as encrypted blobs — decrypted only if shared key is still valid.

### Key Generation

- Secret Chats use DH with pre-defined `g` and `p` (safe prime, 2048-bit).
- Each message is serialized as a JSON object, then encrypted with AES using a key derived from SHA-256 of the DH result.
- Secret Chats support `msg_id`, `seq_no`, and `layer` to mimic Telegram's layering protocol.

### Message Integrity

- Cloud Chat:
  - Each message generates a SHA256 `msg_key` based on `auth_key` and content.
  - Used in deriving AES key + IV.
- Secret Chat:
  - Keys are derived using SHA256 of BigInt DH shared key.
  - IVs and ciphertexts are encoded in Base64 and decrypted on the client.

### Forward Secrecy (Simulated)

- Re-keying is possible by re-initiating DH after a session reset.
- Old keys are never reused, mimicking **Perfect Forward Secrecy**.

- ## Testing & Validation

This application was tested rigorously to ensure both encryption correctness and chat functionality. Below are the key testing steps and outcomes:

###  Functional Testing

- **User Registration & Login**  
  - Tested signup with username/email/phone.
  - Validated session persistence and redirection.

- **Chat Functionality (Cloud Mode)**  
  - Message sending, delivery, read receipts (✔, ✔✔, ✅).
  - Media/file upload and encrypted transfer.
  - In-chat UI search (by sender, type, date).

- **Secret Chat Mode**  
  - Initiated DH key exchange from either client.
  - Verified that shared keys matched on both sides.
  - Confirmed message payload is unreadable to the server.
  - Tested session re-keying by switching users.

## 🔐 Encryption Validation

- Confirmed **AES-256 IGE** encryption integrity in Cloud Chat using logs.
- Verified **msg_key**, **salt**, **session_id**, and **auth_key_id** were unique per message.
- Logged decrypted payloads in secret chat to ensure **correct end-to-end decryption**.
- Simulated offline message delivery (message queued, delivered after re-login).
- Verified server cannot decrypt or read any `chat_mode='secret'` messages.

## Sequence Number & Layer Testing

- Messages in Secret Chat carry:
  - `seq_no`: incremented independently by each user.
  - `layer`: hardcoded to `46`, consistent with MTProto v2 structure.
- Warnings logged for any mismatch in `seq_no` to ensure **replay protection**.

##  Cross-Device Testing

- Two users logged in on different browsers/devices.
- Secret chat re-initiated and verified for symmetric shared keys.
- Delivery and rendering of encrypted payload verified between tabs.

All major encryption, routing, and status features were verified for correctness and compliance with the MTProto-inspired design.

---

## Features

- User Registration and Login:
  - Register using email, phone, or username.
  - Login securely with password-based authentication.

- Cloud Chat Mode:
  - Messages are encrypted on the server using AES-256 IGE.
  - Server can decrypt messages for cloud storage and delivery.
  - Uses MTProto-inspired fields: `salt`, `session_id`, `msg_id`, `seq_no`, etc.

- Secret Chat Mode:
  - Fully end-to-end encrypted between clients.
  - Implements classic Diffie-Hellman key exchange for generating shared keys.
  - Messages are encrypted client-side using AES-256 IGE.
  - Server relays encrypted data without access to plaintext.

- Real-Time Messaging:
  - WebSocket-based (via Flask-SocketIO) chat with instant message delivery.
  - Read receipts (✔, ✔✔, ✅), typing indicators, and message statuses.

- Message Queuing:
  - Messages sent while a user is offline are queued and delivered on reconnection.
  - Secret chat messages remain encrypted blobs until the key is re-established.

- Media Support:
  - Upload and send files, images, and thumbnails.
  - Files are stored encrypted.

- Chat UI:
  - Cloud and Secret chats are visually distinct with separate chat boxes.
  - Dark-mode vignette for secret chat sessions.
  - Status labels, mode selectors, and clean mobile-responsive design.
 
## Conclusion

This project successfully demonstrates a fully functional secure messaging system using MTProto 2.0 principles. It includes two distinct modes:

- **Cloud Chat**: Messages are encrypted client-to-server using AES-256 IGE and decrypted on the server for delivery and storage.
- **Secret Chat**: Messages are encrypted end-to-end using client-side Diffie-Hellman key exchange, AES-256 IGE encryption, and stored only as ciphertext on the server.

Key highlights:
- Real-time messaging via WebSockets
- Media/file support with encrypted uploads
- Typing indicators and read receipts
- UI toggle for chat mode switching
- No plaintext message is visible in Secret Chats—even if intercepted

This project balances user experience with strong cryptographic protections and demonstrates practical implementation of MTProto encryption strategies. It offers a robust foundation for further development or academic exploration in secure communications.
