import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from backend.memory import (
    add_message,
    get_recent_history
)


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env file")


# Gemini client with a 30-second timeout
client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(timeout=30000)
)


SYSTEM_PROMPT = """
You are GenAI Intern Bot.

You are a friendly and helpful AI assistant.

Your responsibilities:

1. Explain technical concepts in beginner-friendly language.
2. Give practical examples.
3. Help users understand programming and AI concepts.
4. Remember the context provided in the conversation.
5. Provide clear and structured answers.
"""


# Approximate context budget for conversation messages
MAX_CONTEXT_TOKENS = 6000


def estimate_tokens(text):
    """
    Rough token estimation.
    A common approximation is 1 token per 4 characters.
    Actual token counts vary by language and content.
    """
    return max(1, len(text) // 4)


def build_context(history, user_message):
    """
    Select the most recent complete conversation turns
    that fit within our context budget.
    """

    system_tokens = estimate_tokens(SYSTEM_PROMPT)
    current_message_tokens = estimate_tokens(user_message)

    available_tokens = (
        MAX_CONTEXT_TOKENS
        - system_tokens
        - current_message_tokens
    )

    selected_messages = []

    # Process history in complete user/assistant pairs,
    # starting with the most recent pair.
    for i in range(len(history) - 2, -1, -2):
        pair = history[i:i + 2]

        pair_tokens = sum(
            estimate_tokens(message["content"])
            for message in pair
        )

        if pair_tokens > available_tokens:
            break

        selected_messages = pair + selected_messages
        available_tokens -= pair_tokens

    contents = []

    for message in selected_messages:
        role = "user" if message["role"] == "user" else "model"

        contents.append({
            "role": role,
            "parts": [{"text": message["content"]}]
        })

    # Always include the current user message
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    return contents


MODEL_NAME = "gemini-3.6-flash"

MAX_RETRIES = 3


class ChatbotServiceError(Exception):

    def __init__(self, message, status_code=503):
        super().__init__(message)
        self.status_code = status_code


def generate_reply(conversation_id, user_message):

    history = get_recent_history(conversation_id)

    contents = build_context(
    history,
    user_message
)

    # Convert conversation history into Gemini format
    for message in history:

        role = "user" if message["role"] == "user" else "model"

        contents.append({
            "role": role,
            "parts": [{"text": message["content"]}]
        })

    # Add current message
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    # Retry mechanism
    for attempt in range(MAX_RETRIES):

        try:

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config={
                    "system_instruction": SYSTEM_PROMPT
                }
            )

            bot_reply = response.text

            if not bot_reply:
                raise ChatbotServiceError(
                    "Gemini returned an empty response.",
                    502
                )

            # Save history only after successful response
            add_message(conversation_id, "user", user_message)
            add_message(conversation_id, "assistant", bot_reply)

            return bot_reply

        except ChatbotServiceError:
            raise

        except Exception as error:

            print("Gemini API error:", repr(error))

            code = getattr(error, "code", None)

            # Handle errors that may be temporary
            message = str(error).lower()

            temporary_error = (
                code in [408, 429, 500, 502, 503, 504]
                or isinstance(error, TimeoutError)
                or "timeout" in message
                or "timed out" in message
                or "connection" in message
                or "temporarily unavailable" in message
            )

            if temporary_error and attempt < MAX_RETRIES - 1:

                wait_time = 2 ** attempt

                print(
                    f"Retrying in {wait_time} seconds..."
                )

                time.sleep(wait_time)

                continue

            if code == 429:
                status_code = 429
            elif code in [408, 500, 502, 503, 504] or temporary_error:
                status_code = 503
            else:
                status_code = 502

            raise ChatbotServiceError(
                "Unable to get a response from the AI service. Please try again.",
                status_code
            ) from error

    raise ChatbotServiceError(
        "AI service is temporarily unavailable.",
        503
    )



def generate_reply_stream(conversation_id, user_message):
    history = get_recent_history(conversation_id)

    contents = build_context(history, user_message)

    full_reply = []

    try:
        response_stream = client.models.generate_content_stream(
            model=MODEL_NAME,
            contents=contents,
            config={
                "system_instruction": SYSTEM_PROMPT
            }
        )

        # Receive Gemini response in chunks
        for chunk in response_stream:
            chunk_text = chunk.text

            if chunk_text:
                full_reply.append(chunk_text)

                yield {
                    "type": "chunk",
                    "text": chunk_text
                }

        # Combine all generated chunks
        bot_reply = "".join(full_reply)

        # Handle empty response
        if not bot_reply.strip():
            yield {
                "type": "error",
                "message": "Gemini returned an empty response. Please try again."
            }
            return

        # Save conversation only after successful generation
        add_message(
            conversation_id,
            "user",
            user_message
        )

        add_message(
            conversation_id,
            "assistant",
            bot_reply
        )

        yield {
            "type": "done"
        }

    except Exception as exc:

        print("Gemini streaming error:", repr(exc))

        error_message = str(exc).lower()

        if "429" in error_message or "resource_exhausted" in error_message:
            message = (
                "Gemini API daily quota exceeded. "
                "Please try again later."
            )

        elif "503" in error_message or "unavailable" in error_message:
            message = (
                "Gemini service is temporarily unavailable. "
                "Please try again later."
            )

        elif "504" in error_message or "deadline_exceeded" in error_message:
            message = (
                "Gemini request timed out. Please try again."
            )

        elif "401" in error_message or "403" in error_message:
            message = (
                "Gemini API authentication failed. "
                "Please check your API key and permissions."
            )

        else:
            message = (
                "Unable to complete the AI response. "
                "Please try again."
            )

        yield {
            "type": "error",
            "message": message
        }
