# MTProto-Based End-to-End Encrypted Web Messenger

This project is a secure, modular, and web-based messaging system built using Flask, Socket.IO, and MTProto-inspired encryption. It supports both **Cloud Chats** (server-readable, AES-IGE encrypted) and **Secret Chats** (fully end-to-end encrypted with Diffie-Hellman key exchange).

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
