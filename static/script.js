
let conversationId = null;

const chatBox = document.getElementById("chat-box");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat-btn");
const conversationList = document.getElementById("conversation-list");

// Display a message
function addMessage(message, sender) {
    const messageDiv = document.createElement("div");
    messageDiv.classList.add("message", sender);

    if (sender === "bot") {
        const html = marked.parse(message);
        messageDiv.innerHTML = DOMPurify.sanitize(html);
    } else {
        messageDiv.textContent = message;
    }

    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Create a new conversation
async function createConversation() {
    const response = await fetch("/conversations", {
        method: "POST"
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Unable to create conversation");
    }

    conversationId = data.conversation_id;
    await renderConversations();
}

// Load all conversations into sidebar
async function renderConversations() {
    const response = await fetch("/conversations");
    const conversations = await response.json();

    if (!response.ok) {
        throw new Error("Unable to load conversations");
    }

    conversationList.innerHTML = "";

    conversations.reverse().forEach(conversation => {
        const item = document.createElement("div");
        item.classList.add("conversation-item");

        const openButton = document.createElement("button");
        openButton.classList.add("conversation-open");
        openButton.textContent = conversation.title;

        if (conversation.conversation_id === conversationId) {
            openButton.classList.add("active");
        }

        openButton.title = conversation.title;

        openButton.addEventListener("click", () => {
            loadConversation(conversation.conversation_id);
        });

        const deleteButton = document.createElement("button");
        deleteButton.classList.add("delete-chat-btn");
        deleteButton.textContent = "✕";
        deleteButton.title = "Delete conversation";

        deleteButton.addEventListener("click", async () => {
            if (!confirm("Delete this conversation?")) return;

            try {
                await deleteConversation(conversation.conversation_id);
                await renderConversations();
            } catch (error) {
                alert(error.message);
            }
        });

        item.appendChild(openButton);
        item.appendChild(deleteButton);
        conversationList.appendChild(item);
    });
}

// Send a message

async function sendMessage() {
    const message = userInput.value.trim();

    if (!message || sendBtn.disabled) return;

    sendBtn.disabled = true;

    try {
        if (!conversationId) {
            await createConversation();
        }

        addMessage(message, "user");
        userInput.value = "";

        // Create an empty AI message bubble
        const botMessage = document.createElement("div");
        botMessage.classList.add("message", "bot");
        botMessage.textContent = "Thinking...";
        chatBox.appendChild(botMessage);

        try {
            const response = await fetch("/chat/stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: conversationId
                })
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || "Request failed");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            let buffer = "";
            let fullReply = "";
            let streamError = null;
            let completed = false;

            botMessage.textContent = "";

            while (true) {
                const { value, done } = await reader.read();

                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                const events = buffer.split("\n\n");
                buffer = events.pop();

                for (const event of events) {
                    const line = event
                        .split("\n")
                        .find(line => line.startsWith("data: "));

                    if (!line) continue;

                    const data = JSON.parse(line.slice(6));

                    if (data.type === "start") {
                        conversationId = data.conversation_id;
                    }

                    if (data.type === "chunk") {
                        fullReply += data.text;
                        botMessage.textContent = fullReply;
                        chatBox.scrollTop = chatBox.scrollHeight;
                    }

                    if (data.type === "error") {
                        streamError = data.message;
                    }

                    if (data.type === "done") {
                        completed = true;
                    }
                }
            }

            // Render Markdown after streaming is complete
            if (fullReply) {
                botMessage.innerHTML = DOMPurify.sanitize(
                    marked.parse(fullReply)
                );
            } else {
                botMessage.textContent = "";
            }

            if (streamError) {
                addMessage("Error: " + streamError, "bot");
            } else if (!completed) {
                addMessage(
                    "Error: The streaming connection ended unexpectedly.",
                    "bot"
                );
            }

            await renderConversations();

        } catch (error) {
            botMessage.remove();
            addMessage("Error: " + error.message, "bot");
        }

    } catch (error) {
        addMessage("Error: " + error.message, "bot");
    } finally {
        sendBtn.disabled = false;
        userInput.focus();
    }
}


// Start a fresh chat
function newChat() {
    if (sendBtn.disabled) return;

    conversationId = null;
    chatBox.innerHTML = "";

    addMessage(
        "Hello! 👋 I'm your AI assistant. How can I help you?",
        "bot"
    );

    renderConversations();
}

// Open an existing conversation
async function loadConversation(id) {
    if (sendBtn.disabled) return;

    try {
        const response = await fetch(`/conversations/${id}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Unable to load conversation");
        }

        conversationId = id;
        chatBox.innerHTML = "";

        data.messages.forEach(message => {
            addMessage(
                message.content,
                message.role === "user" ? "user" : "bot"
            );
        });

        await renderConversations();

    } catch (error) {
        addMessage("Error: " + error.message, "bot");
    }
}

// Delete a conversation
async function deleteConversation(id) {
    const response = await fetch(`/conversations/${id}`, {
        method: "DELETE"
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Unable to delete conversation");
    }

    if (conversationId === id) {
        conversationId = null;
        chatBox.innerHTML = "";

        addMessage(
            "Conversation deleted. Start a new chat!",
            "bot"
        );
    }
}

// Event listeners
sendBtn.addEventListener("click", sendMessage);
newChatBtn.addEventListener("click", newChat);

userInput.addEventListener("keydown", event => {
    if (event.key === "Enter") {
        sendMessage();
    }
});

// Load sidebar when page opens
renderConversations();
