# GenAI Conversational Chatbot

A full-stack AI conversational chatbot built using Python, Flask, and Google's Gemini API. It supports multi-turn conversations, persistent chat history, streaming responses, and conversation management.

## Features

- **AI-powered conversations:** Generate responses using Google's Gemini API.
- **Multi-turn memory:** Maintain conversation context across messages.
- **Persistent storage:** Store conversations and messages using SQLite.
- **Streaming responses:** Display AI responses as they are generated.
- **Conversation management:** Create, view, switch between, and delete conversations.
- **Context management:** Manage conversation history using an approximate token budget.
- **Markdown rendering:** Display formatted AI responses.
- **Input validation:** Validate requests and reject invalid or oversized messages.
- **Error handling:** Handle API failures and rate limits.
- **Automated testing:** Test backend functionality using pytest.

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python |
| Backend | Flask |
| AI Model API | Google Gemini API |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |
| Markdown | Marked.js |
| HTML Sanitization | DOMPurify |
| Testing | Pytest |

## Project Structure

```text
genai-conversational-chatbot/
│
├── app.py
├── chatbot.db
├── requirements.txt
├── .env.example
├── .gitignore
│
├── backend/
│   ├── __init__.py
│   ├── chatbot.py
│   └── memory.py
│
├── templates/
│   └── index.html
│
├── static/
│   ├── style.css
│   └── script.js
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_app.py
```

## Getting Started

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd genai-conversational-chatbot
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Get an API key from [Google AI Studio](https://aistudio.google.com/).

Never share or commit your actual API key.

### 5. Run the application

```bash
python app.py
```

Open your browser:

```text
http://127.0.0.1:5000
```

## Running Tests

Run the automated tests:

```bash
python -m pytest tests/ -v
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Load chatbot interface |
| POST | `/conversations` | Create a conversation |
| GET | `/conversations` | List conversations |
| GET | `/conversations/<id>` | Retrieve conversation history |
| DELETE | `/conversations/<id>` | Delete a conversation |
| POST | `/chat` | Generate a chatbot response |
| POST | `/chat/stream` | Generate a streaming response |

## Architecture

```text
                 User
                  |
                  v
          HTML / CSS / JS
                  |
                  v
             Flask API
                  |
          +-------+-------+
          |               |
          v               v
    Chatbot Service    SQLite DB
          |
          v
     Gemini API
          |
          v
    AI Response
          |
          v
       Frontend
```

## Security Notes

- API keys are stored in environment variables.
- `.env` should never be committed.
- User messages are validated before processing.
- Markdown output is sanitized before rendering.

## Future Improvements

- User authentication and private conversations
- Production deployment
- More accurate token counting
- Rate limiting and usage monitoring
- Export and download conversation history

## Author

**Abhiram**

Built as a Generative AI internship project to explore LLM integration, backend development, conversation memory, streaming, and API design.
