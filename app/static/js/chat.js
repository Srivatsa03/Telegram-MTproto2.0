// Connect to Socket.IO server

const socket = io.connect(window.location.origin);
const pendingMessages = {};
const keyExchangeComplete = {}; 
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
    const label = document.getElementById("chatModeLabel");

    if (mode === 'secret') {
        cloudBox.style.display = "none";
        secretBox.style.display = "block";
        label.textContent = "🔐 Secret Chat";
    } else {
        cloudBox.style.display = "block";
        secretBox.style.display = "none";
        label.textContent = "☁️ Cloud Chat";
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

// Handle incoming public key (from recipient)
socket.on("receive_public_key", (data) => {
    console.log("🔑 Received public key from user", data.sender_id);
    const recipientEntry = dhSharedKeys[data.sender_id];

    if (!recipientEntry) {
        console.log("❌ No private key entry for this user yet! Generating one...");
        const privateKey = generatePrivateKey();
        const publicKey = computePublicKey(privateKey);

        dhSharedKeys[data.sender_id] = { privateKey, sharedSecret: null };

        console.log(`🚀 Sending public key to user ${data.sender_id}`);
        socket.emit("exchange_public_key", {
            sender_id: userId,
            receiver_id: data.sender_id,
            public_key: publicKey.toString()
        });
    }
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

    const otherPublicKey = BigInt(data.public_key);
    const sharedSecret = computeSharedKey(otherPublicKey, dhSharedKeys[data.sender_id].privateKey);
    dhSharedKeys[data.sender_id].sharedSecret = sharedSecret;
    keyExchangeComplete[data.sender_id] = true;  // ✅ Mark key exchange as complete

    console.log(`✅ Shared secret computed with user ${data.sender_id}`);
});

// Handle incoming message
socket.on("receive_message", (data) => {
    if (data.chat_mode === 'secret') {
        const otherUserId = data.from == userId ? data.to : data.from;
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
            data.text = plainText;
            displayMessage(data, data.from == userId ? "sent" : "received");
        });
    } else if (data.chat_mode === 'cloud') {
        // ✅ Handle Cloud Chat messages directly
        displayMessage(data, data.from == userId ? "sent" : "received");
    }
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

    const payload = {
        sender_id: parseInt(userId),
        receiver_id: receiverId,
        timestamp: new Date().toISOString(),
        msg_id: generateMsgId(),
        salt: generateSalt(),
        session_id: getSessionId()
    };

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
    
        encryptMessageWithAES(sharedEntry.sharedSecret, text).then((encryptedText) => {
            payload.text = encryptedText;
            payload.chat_mode = 'secret';
            socket.emit("send_message", payload);

            input.value = "";
        });
    }
    else {  
        // ✅ Cloud Chat logic (currently missing)
        payload.text = text;
        payload.chat_mode = 'cloud';
        socket.emit("send_message", payload);
    
        input.value = "";  // ✅ Clears input for Cloud Chat too
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

    bubble.setAttribute("data-msg-id", data.id || "");
    bubble.innerHTML = `
        <div class="message-text">${data.text}</div>
        <div class="message-meta">
            ${timestamp} <span class="message-status">${data.status || "✔"}</span>
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

    fetch(`/status/${user.id}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById("userStatus").textContent = data.status === "online"
                ? "Online"
                : `${data.status}`;
        });

    loadChatHistory(user.id);

    // 💡 Add this:
    if (chatMode === 'secret') {
        initiateSecretChat(user.id);  // Re-initiate DH exchange
    }

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

        document.getElementById("cloudChatBox").innerHTML = "";
        document.getElementById("secretChatBox").innerHTML = "";
        document.getElementById("chatWith").innerText = "Select a user to start chatting";
        document.getElementById("userStatus").textContent = "";
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