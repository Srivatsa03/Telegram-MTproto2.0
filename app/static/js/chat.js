// Connect to Socket.IO server

const socket = io.connect(window.location.origin);
const pendingMessages = {};
const keyExchangeComplete = {}; 
const seqNumbers = {};

// Join user's private room on page load
const userId = localStorage.getItem("user_id");
if (userId) {
    socket.emit("join", { user_id: parseInt(userId) });
}

// Default chat mode (cloud or secret)
let chatMode = 'cloud'; // Default mode

// Store DH shared keys (per user)
const dhSharedKeys = {}; // { recipientId: sharedSecret }

// Set chat mode (called from UI)
function setChatMode(mode) {
    chatMode = mode;
    console.log(`Chat mode set to: ${chatMode}`);
  
    const cloudBox = document.getElementById("cloudChatBox");
    const secretBox = document.getElementById("secretChatBox");
    const body = document.body;   // 💡 Target body
    const chatContainer = document.getElementById("chatBox");
  
    if (!cloudBox || !secretBox) {
      console.error("Chat boxes not found!");
      return;
    }
  
    if (mode === 'secret') {
      cloudBox.style.display = "none";
      secretBox.style.display = "block";
  
      secretBox.classList.add("secret-chat-bg");
  
      // 🖤 Switch full body to dark mode
      body.classList.add("secret-body");
  
    } else {
      cloudBox.style.display = "block";
      secretBox.style.display = "none";
  
      secretBox.classList.remove("secret-chat-bg");
  
      // ☀️ Switch full body back to light mode
      body.classList.remove("secret-body");
    }
  }

// Initiate DH exchange (when Secret Chat starts)
async function initiateSecretChat(recipientId) {
    const privateKey = generatePrivateKey();
    const publicKey = computePublicKey(privateKey);
    console.log(`🚀 Sending public key to user ${recipientId}`);
    socket.emit("exchange_public_key", {
        sender_id: userId,
        receiver_id: recipientId,
        public_key: publicKey.toString()
    });
    dhSharedKeys[recipientId] = { privateKey, sharedSecret: null };
}

socket.on("receive_public_key", (data) => {
    console.log("🔑 Received public key from user", data.sender_id);

    const recipientEntry = dhSharedKeys[data.sender_id];
    let privateKey, publicKey;

    if (!recipientEntry) {
        // ✅ No private key yet → generate one
        console.log("❌ No private key entry for this user yet! Generating one...");
        privateKey = generatePrivateKey();
        publicKey = computePublicKey(privateKey);

        // ✅ Save private key
        dhSharedKeys[data.sender_id] = { privateKey, sharedSecret: null };

        // Notify user that Secret Chat was initiated
        // Try to fetch the username dynamically
        fetch(`/user_info/${data.sender_id}`)
            .then(res => res.json())
            .then(info => {
                const username = info.username || `User ${data.sender_id}`;
                showToast(`🔐 Secret Chat initiated by ${username}`);
            })
            .catch(err => {
                console.error("Failed to fetch username:", err);
                showToast(`🔐 Secret Chat initiated by user ${data.sender_id}`);
            });

        // ✅ Send back our public key
        console.log(`🚀 Sending public key to user ${data.sender_id}`);
        socket.emit("exchange_public_key", {
            sender_id: userId,
            receiver_id: data.sender_id,
            public_key: publicKey.toString()
        });
    }

    // ✅ Compute shared secret
    const otherPublicKey = BigInt(data.public_key);
    const sharedSecret = computeSharedKey(otherPublicKey, dhSharedKeys[data.sender_id].privateKey);
    dhSharedKeys[data.sender_id].sharedSecret = sharedSecret;
    keyExchangeComplete[data.sender_id] = true;

    console.log(`✅ Shared secret computed with user ${data.sender_id}`);

    const initiateBtn = document.getElementById("initiateSecretBtn");
    if (initiateBtn) {
        initiateBtn.classList.remove("btn-warning");
        initiateBtn.classList.add("btn-success");
        initiateBtn.innerHTML = "✅ Secret Chat Ready";
        initiateBtn.disabled = true;
    }

    Swal.fire({
        icon: 'success',
        title: 'Secret Chat Ready!',
        text: 'You are now chatting securely 🔐',
        timer: 2000,
        showConfirmButton: false
    });

    // ✅ Process any queued messages (history or real-time)
    if (pendingMessages[data.sender_id]) {
        console.log(`🔓 Decrypting ${pendingMessages[data.sender_id].length} queued messages (history + real-time)...`);
        pendingMessages[data.sender_id].forEach(msg => {
            decryptMessageWithAES(sharedSecret, msg.text).then((plainText) => {
                msg.text = plainText;
                const type = msg.from == userId ? "sent" : "received";
                displayMessage(msg, type);
            });
        });
        delete pendingMessages[data.sender_id];
    }
});

// Handle incoming message
socket.on("receive_message", (data) => {
    const otherUserId = data.from == userId ? data.to : data.from;

    // ✅ Initialize sequence numbers for this user
    if (!seqNumbers[otherUserId]) {
        seqNumbers[otherUserId] = { outgoing: 0, incoming: 0 };
    }

    if (data.chat_mode === 'secret') {
        const sharedEntry = dhSharedKeys[otherUserId];

        if (!sharedEntry || !sharedEntry.sharedSecret) {
            console.warn("🔄 Queuing message, shared key not ready yet!");
            if (!pendingMessages[otherUserId]) {
                pendingMessages[otherUserId] = [];
            }
            pendingMessages[otherUserId].push(data);  // Queue message
            return;
        }

        decryptMessageWithAES(sharedEntry.sharedSecret, data.text).then((plainText) => {
            const decryptedPayload = JSON.parse(plainText);

            const receivedSeqNo = decryptedPayload.seq_no;
            const expectedSeqNo = seqNumbers[otherUserId].incoming + 1;

            if (receivedSeqNo !== expectedSeqNo) {
                
            } else {
                console.log(`Correct incoming sequence: ${receivedSeqNo}`);
            }

            // ✅ Always update incoming seq number
            seqNumbers[otherUserId].incoming = receivedSeqNo;

            // ✅ Layer check (bonus)
            if (decryptedPayload.layer && decryptedPayload.layer > 46) {
                console.warn(`⚠️ Received message with newer layer: ${decryptedPayload.layer}`);
            }

            // ✅ Full Decrypted payload log
            console.log(`🔓 Decrypted Payload:`);
            console.log(`- Text: ${decryptedPayload.text}`);
            console.log(`- Msg ID: ${decryptedPayload.msg_id}`);
            console.log(`- Seq No: ${decryptedPayload.seq_no}`);
            console.log(`- Timestamp (Unix): ${decryptedPayload.time}`);
            console.log(`- Sender ID: ${decryptedPayload.sender_id}`);
            console.log(`- Receiver ID: ${decryptedPayload.receiver_id}`);

            data.text = decryptedPayload.text;
            displayMessage(data, data.from == userId ? "sent" : "received");
        });
    } else if (data.chat_mode === 'cloud') {
        displayMessage(data, data.from == userId ? "sent" : "received");
    }

    // ✅ Message status ack
    if (data.id && data.to == userId) {
        socket.emit("message_status", {
            message_id: data.id,
            status: "✔✔"
        });
    }
});

// Handle message status update (✔, ✔✔, ✅)
socket.on("message_status", (data) => {
    updateMessageStatus(data.message_id, data.status);
});

// Send new message
function sendMessage() {
    const input = document.getElementById("messageInput");
    const text = input.value;
    const receiverId = parseInt(document.getElementById("receiverId").value);

    if (!text || !receiverId) return;

    // Initialize sequence tracking
    if (!seqNumbers[receiverId]) {
        seqNumbers[receiverId] = { outgoing: 0, incoming: 0 };
    }

    if (chatMode === 'secret') {
        if (!keyExchangeComplete[receiverId]) {
            console.error("❌ Key exchange not complete yet! Wait.");
            return;
        }

        const sharedEntry = dhSharedKeys[receiverId];
        if (!sharedEntry || !sharedEntry.sharedSecret) {
            console.error("❌ Shared key not established yet!");
            return;
        }

        // 🧠 Increment outgoing sequence number
        seqNumbers[receiverId].outgoing += 1;
        const seq_no = seqNumbers[receiverId].outgoing;
        const layer = 46;  // Bonus: like Telegram MTProto layers

        const msg_id = generateMsgId();
        const salt = generateSalt();
        const session_id = getSessionId();

        const payloadObject = {
            text: text,
            time: Math.floor(Date.now() / 1000),
            msg_id: msg_id,
            seq_no: seq_no,
            sender_id: userId,
            receiver_id: receiverId,
            layer: layer
        };

        console.log(`🔧 [SECRET CHAT] Preparing MTProto-like payload:`);
        console.log(`- Salt: ${salt}`);
        console.log(`- Session ID: ${session_id}`);
        console.log(`- Msg ID: ${msg_id}`);
        console.log(`- Seq No (OUT): ${seq_no}`);
        console.log(`- Layer: ${layer}`);
        console.log(`- Payload:`, payloadObject);

        encryptMessageWithAES(sharedEntry.sharedSecret, JSON.stringify(payloadObject)).then((encryptedText) => {
            const payload = {
                sender_id: parseInt(userId),
                receiver_id: receiverId,
                text: encryptedText,
                chat_mode: 'secret',
                salt: salt,
                session_id: session_id,
                msg_id: msg_id,
                seq_no: seq_no,
                timestamp: new Date().toISOString(),
                layer: layer
            };
            socket.emit("send_message", payload);
            input.value = "";
        });

    } else {
        // ☁️ Cloud Chat
        const payload = {
            sender_id: parseInt(userId),
            receiver_id: receiverId,
            text: text,
            chat_mode: 'cloud',
            timestamp: new Date().toISOString(),
            msg_id: generateMsgId(),
            salt: generateSalt(),
            session_id: getSessionId()
        };

        socket.emit("send_message", payload);
        input.value = "";
    }
}

// Display messages in the chat window
function displayMessage(data, type) {
    const targetBox = data.chat_mode === 'secret'
        ? document.getElementById("secretChatBox")
        : document.getElementById("cloudChatBox");

    const messageWrapper = document.createElement("div");
    const timestamp = new Date(data.timestamp || Date.now()).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit'
    });

    messageWrapper.classList.add("d-flex", "mb-2");
    messageWrapper.classList.add(type === "sent" ? "justify-content-end" : "justify-content-start");

    const bubble = document.createElement("div");
    bubble.classList.add("message-bubble", type === "sent" ? "message-sent" : "message-received");

    // 💡 Differentiate cloud vs secret visually
    bubble.classList.add(data.chat_mode === 'secret' ? "secret-chat" : "cloud-chat");

    bubble.innerHTML = `
        <div class="message-text">${data.text}</div>
        <div class="message-meta small text-muted mt-1">
            ${timestamp} 
            <span class="message-status">${data.status || "✔"}</span>
            <span class="badge ${data.chat_mode === 'secret' ? 'bg-warning text-dark' : 'bg-secondary'} ms-2">
                ${data.chat_mode === 'secret' ? 'Secret' : 'Cloud'}
            </span>
        </div>
    `;

    messageWrapper.appendChild(bubble);
    targetBox.appendChild(messageWrapper);
    targetBox.scrollTop = targetBox.scrollHeight;

    if (type === "received" && data.id) {
        socket.emit("mark_read", { message_id: data.id });
    }
}

// Update status icon for a message
function updateMessageStatus(messageId, status) {
    const el = document.querySelector(`[data-msg-id="${messageId}"] .message-status`);
    if (el) el.textContent = status;
}

// Send file
function sendFile(input) {
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("sender_id", userId);
    formData.append("receiver_id", document.getElementById("receiverId").value);

    fetch("/chat/upload", {
        method: "POST",
        body: formData
    })
    .then((res) => res.json())
    .then((data) => {
        socket.emit("send_message", {
            sender_id: parseInt(userId),
            receiver_id: parseInt(data.receiver_id),
            text: data.filename,
            media_type: data.media_type,
            file_path: data.file_path,
            thumbnail_path: data.thumbnail_path,
            msg_id: generateMsgId(),
            salt: generateSalt(),
            session_id: getSessionId()
        });
    });
}

// Utility functions
function generateMsgId() {
    return Date.now().toString() + Math.floor(Math.random() * 1000);
}

function generateSalt() {
    return Math.random().toString(36).substring(2, 10);
}

function getSessionId() {
    return localStorage.getItem("session_id") || generateSalt();
}

// Load users in dropdown
function loadUsers() {
    fetch("/users")
        .then(res => res.json())
        .then(users => {
            const currentUserId = localStorage.getItem("user_id");
            const select = document.getElementById("receiverId");
            select.innerHTML = "";

            users.forEach(user => {
                if (user.id == currentUserId) return;
                const option = document.createElement("option");
                option.value = user.id;
                option.textContent = `${user.username} (ID: ${user.id})`;
                select.appendChild(option);
            });

            const savedId = localStorage.getItem("recipient_id");
            if (savedId) {
                select.value = savedId;
            }

            select.addEventListener("change", () => {
                localStorage.setItem("recipient_id", select.value);
            });
        });
}

// Load sidebar chat list
function loadChatList() {
    const userId = localStorage.getItem("user_id");
    fetch(`/chat/contacts/${userId}`)
        .then(res => res.json())
        .then(users => {
            const chatList = document.getElementById("chatList");
            chatList.innerHTML = "";
            users.forEach(user => {
                const li = document.createElement("li");
                li.className = "list-group-item list-group-item-action";
                li.textContent = user.username;
                li.dataset.userId = user.id;
                li.onclick = () => openChatWith(user);
                chatList.appendChild(li);
            });
        });
}

// Open a specific user chat
function openChatWith(user) {
    document.getElementById("chatWith").innerText = `Chatting with: ${user.username}`;
    document.getElementById("receiverId").value = user.id;
    localStorage.setItem("recipient_id", user.id);

    // ✅ Safe toggle for online/offline status badges
    fetch(`/status/${user.id}`)
        .then(res => res.json())
        .then(data => {
            const onlineBadge = document.getElementById("onlineStatus");
            const offlineBadge = document.getElementById("offlineStatus");

            if (onlineBadge && offlineBadge) {
                onlineBadge.style.display = data.status === "online" ? "inline-block" : "none";
                offlineBadge.style.display = data.status === "online" ? "none" : "inline-block";
            }
        });

    // ✅ Load chat history for the current user
    loadChatHistory(user.id);

    // ✅ Always re-initiate DH exchange for Secret Chat
    if (chatMode === 'secret') {
        initiateSecretChat(user.id);  // Ensure key exchange happens
    }

    // ✅ Move user to top of chat list
    const chatList = document.getElementById("chatList");
    const clickedItem = [...chatList.children].find(li => li.dataset.userId == user.id);
    if (clickedItem) {
        chatList.removeChild(clickedItem);
        chatList.insertBefore(clickedItem, chatList.firstChild);
    }
}

// Load chat history
function loadChatHistory(withUserId) {
    const myId = localStorage.getItem("user_id");

    // Clear the correct chat box (based on current chat mode)
    const cloudBox = document.getElementById("cloudChatBox");
    const secretBox = document.getElementById("secretChatBox");
    if (chatMode === 'secret') {
        secretBox.innerHTML = "";
    } else {
        cloudBox.innerHTML = "";
    }

    fetch(`/chat/messages/${myId}`)
        .then(res => res.json())
        .then(messages => {
            messages.forEach(msg => {
                if ((msg.from == myId && msg.to == withUserId) || (msg.from == withUserId && msg.to == myId)) {
                    const type = msg.from == myId ? "sent" : "received";
                    displayMessage(msg, type);
                }
            });
        });
}

// On page load
window.onload = () => {
    const userId = localStorage.getItem("user_id");
    if (userId) {
        socket.emit("join", { user_id: parseInt(userId) });
        loadChatList();

        // ✅ Clear both chat boxes
        document.getElementById("cloudChatBox").innerHTML = "";
        document.getElementById("secretChatBox").innerHTML = "";

        // ✅ Reset header and status
        document.getElementById("chatWith").innerText = "Select a user to start chatting";
        document.getElementById("userStatus").textContent = "";

        // ✅ Ensure Cloud Chat box is visible by default
        setChatMode('cloud');
    }
};

// Typing indicator
const messageInput = document.getElementById("messageInput");
messageInput.addEventListener("input", () => {
    const receiverId = document.getElementById("receiverId").value;
    const senderId = localStorage.getItem("user_id");

    if (receiverId && senderId) {
        socket.emit("typing", {
            from: parseInt(senderId),
            to: parseInt(receiverId)
        });
    }
});

let typingTimeout = null;
socket.on("typing", (data) => {
    const receiverId = localStorage.getItem("user_id");
    const currentChatUser = document.getElementById("receiverId").value;

    if (data.from == currentChatUser) {
        const status = document.getElementById("typingStatus");
        status.textContent = `${data.username} is typing...`;
        status.style.display = "block";

        clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => {
            status.style.display = "none";
        }, 2000);
    }
});

function deleteMessage(messageId, forEveryone = false) {
    fetch("/chat/delete_message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message_id: messageId,
            user_id: localStorage.getItem("user_id"),
            delete_for_all: forEveryone
        })
    }).then(res => res.json())
      .then(data => {
        if (data.success) {
            const el = document.querySelector(`[data-msg-id="${messageId}"]`);
            if (el) el.parentElement.remove();
        } else {
            console.error("Message deletion failed");
        }
    });
}