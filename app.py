
import json

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    Response,
    stream_with_context
)

from backend.memory import (
    create_conversation,
    get_history,
    get_all_conversations,
    delete_conversation,
    conversation_exists
)

from backend.chatbot import (
    generate_reply,
    generate_reply_stream,
    ChatbotServiceError
)


# Initialize Flask application
app = Flask(__name__)

# Maximum HTTP request size: 64 KB
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024

# Maximum user message length
MAX_MESSAGE_LENGTH = 4000


# -----------------------------------
# INPUT VALIDATION
# -----------------------------------

def validate_message(data):

    if not isinstance(data, dict):
        return None, "Invalid JSON request"

    message = data.get("message", "")

    if not isinstance(message, str):
        return None, "Message must be text"

    message = message.strip()

    if not message:
        return None, "Message cannot be empty"

    if len(message) > MAX_MESSAGE_LENGTH:
        return None, "Message is too long. Maximum 4000 characters."

    return message, None


# -----------------------------------
# HOME ROUTE
# -----------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------------
# CREATE NEW CONVERSATION
# -----------------------------------

@app.route("/conversations", methods=["POST"])
def new_conversation():

    conversation_id = create_conversation()

    return jsonify({
        "conversation_id": conversation_id,
        "message": "Conversation created successfully"
    }), 201


# -----------------------------------
# GET ALL CONVERSATIONS
# -----------------------------------

@app.route("/conversations", methods=["GET"])
def conversations():

    all_conversations = get_all_conversations()

    result = []

    for conversation_id, history in all_conversations.items():

        first_message = next(
            (
                message["content"]
                for message in history
                if message["role"] == "user"
            ),
            "New conversation"
        )

        result.append({
            "conversation_id": conversation_id,
            "title": first_message[:40],
            "message_count": len(history)
        })

    return jsonify(result), 200


# -----------------------------------
# GET ONE CONVERSATION
# -----------------------------------

@app.route("/conversations/<conversation_id>", methods=["GET"])
def conversation_details(conversation_id):

    if not conversation_exists(conversation_id):
        return jsonify({
            "error": "Conversation not found"
        }), 404

    history = get_history(conversation_id)

    return jsonify({
        "conversation_id": conversation_id,
        "messages": history
    }), 200


# -----------------------------------
# DELETE CONVERSATION
# -----------------------------------

@app.route("/conversations/<conversation_id>", methods=["DELETE"])
def remove_conversation(conversation_id):

    deleted = delete_conversation(conversation_id)

    if not deleted:
        return jsonify({
            "error": "Conversation not found"
        }), 404

    return jsonify({
        "message": "Conversation deleted successfully"
    }), 200


# -----------------------------------
# NORMAL CHAT ENDPOINT
# -----------------------------------

@app.route("/chat", methods=["POST"])
def chat():

    try:

        data = request.get_json(silent=True)

        message, error = validate_message(data)

        if error:
            return jsonify({"error": error}), 400

        conversation_id = data.get("conversation_id")

        if not conversation_id:
            conversation_id = create_conversation()

        elif not isinstance(conversation_id, str):
            return jsonify({
                "error": "Invalid conversation ID"
            }), 400

        elif not conversation_exists(conversation_id):
            return jsonify({
                "error": "Conversation not found"
            }), 404

        bot_response = generate_reply(
            conversation_id,
            message
        )

        return jsonify({
            "conversation_id": conversation_id,
            "user_message": message,
            "bot_response": bot_response
        }), 200

    except ChatbotServiceError as error:

        return jsonify({
            "error": str(error)
        }), error.status_code

    except Exception as error:

        app.logger.exception("Chat endpoint error")

        return jsonify({
            "error": "Internal server error"
        }), 500


# -----------------------------------
# STREAMING CHAT ENDPOINT
# -----------------------------------

@app.route("/chat/stream", methods=["POST"])
def chat_stream():

    data = request.get_json(silent=True)

    message, error = validate_message(data)

    if error:
        return jsonify({"error": error}), 400

    conversation_id = data.get("conversation_id")

    if not conversation_id:
        conversation_id = create_conversation()

    elif not isinstance(conversation_id, str):
        return jsonify({
            "error": "Invalid conversation ID"
        }), 400

    elif not conversation_exists(conversation_id):
        return jsonify({
            "error": "Conversation not found"
        }), 404

    def event_stream():

        yield (
            "data: "
            + json.dumps({
                "type": "start",
                "conversation_id": conversation_id
            })
            + "\n\n"
        )

        for event in generate_reply_stream(
            conversation_id,
            message
        ):

            yield (
                "data: "
                + json.dumps(event)
                + "\n\n"
            )

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )


# -----------------------------------
# REQUEST SIZE ERROR HANDLER
# -----------------------------------

@app.errorhandler(413)
def request_too_large(error):

    return jsonify({
        "error": "Request is too large."
    }), 413


# -----------------------------------
# RUN APPLICATION
# -----------------------------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
