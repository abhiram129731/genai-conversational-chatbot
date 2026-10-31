
import pytest

import app as app_module
import backend.memory as memory


@pytest.fixture(autouse=True)
def setup_test_database(tmp_path, monkeypatch):
    """Use a separate temporary database for every test."""

    test_db = tmp_path / "test_chatbot.db"

    monkeypatch.setattr(memory, "DB_PATH", test_db)

    memory.init_db()


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as test_client:
        yield test_client


# --------------------------------
# HOME PAGE TEST
# --------------------------------

def test_home_page(client):
    response = client.get("/")

    assert response.status_code == 200


# --------------------------------
# INPUT VALIDATION TESTS
# --------------------------------

def test_empty_message(client):
    response = client.post(
        "/chat",
        json={"message": ""}
    )

    assert response.status_code == 400


def test_non_string_message(client):
    response = client.post(
        "/chat",
        json={"message": 123}
    )

    assert response.status_code == 400


def test_message_too_long(client):
    response = client.post(
        "/chat",
        json={"message": "a" * 4001}
    )

    assert response.status_code == 400


# --------------------------------
# CHAT API TESTS
# --------------------------------

def test_chat_success(client, monkeypatch):

    conversation_id = memory.create_conversation()

    monkeypatch.setattr(
        app_module,
        "generate_reply",
        lambda conversation_id, message: "Hello! I am your AI assistant."
    )

    response = client.post(
        "/chat",
        json={
            "message": "Hello",
            "conversation_id": conversation_id
        }
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["bot_response"] == "Hello! I am your AI assistant."


def test_unknown_conversation(client):

    response = client.post(
        "/chat",
        json={
            "message": "Hello",
            "conversation_id": "invalid-id"
        }
    )

    assert response.status_code == 404


# --------------------------------
# STREAMING API TEST
# --------------------------------

def test_streaming_chat(client, monkeypatch):

    conversation_id = memory.create_conversation()

    def fake_stream(conversation_id, message):
        yield {"type": "chunk", "text": "Hello"}
        yield {"type": "chunk", "text": " there!"}
        yield {"type": "done"}

    monkeypatch.setattr(
        app_module,
        "generate_reply_stream",
        fake_stream
    )

    response = client.post(
        "/chat/stream",
        json={
            "message": "Hello",
            "conversation_id": conversation_id
        },
        buffered=True
    )

    assert response.status_code == 200

    assert b"Hello" in response.data
    assert b"there!" in response.data
    assert b'"type": "done"' in response.data


# --------------------------------
# DATABASE TESTS
# --------------------------------

def test_create_and_save_conversation():

    conversation_id = memory.create_conversation()

    memory.add_message(
        conversation_id,
        "user",
        "Explain Python"
    )

    memory.add_message(
        conversation_id,
        "assistant",
        "Python is a programming language."
    )

    history = memory.get_history(conversation_id)

    assert len(history) == 2

    assert history[0]["content"] == "Explain Python"

    assert history[1]["content"] == (
        "Python is a programming language."
    )


def test_delete_conversation():

    conversation_id = memory.create_conversation()

    memory.add_message(
        conversation_id,
        "user",
        "Test message"
    )

    deleted = memory.delete_conversation(conversation_id)

    assert deleted is True

    assert memory.conversation_exists(conversation_id) is False


# --------------------------------
# CONVERSATION LIST TEST
# --------------------------------

def test_get_conversations(client):

    conversation_id = memory.create_conversation()

    memory.add_message(
        conversation_id,
        "user",
        "My first test conversation"
    )

    response = client.get("/conversations")

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1

    assert data[0]["title"] == "My first test conversation"
