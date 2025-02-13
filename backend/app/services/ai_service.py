import openai
from app.models.chat_session import ChatSession
from app.models.user_summary import UserSummary
import json
from datetime import datetime, timezone
from config import Config
from flask import request
import tiktoken

client = openai
client.api_key = Config.OPENAI_API_KEY
model = "gpt-4o-mini"


def generate_ai_response(messages, additional_system_prompt, user_summary=None):
    """
    Generate AI response based on messages and context
    """
    try:
        system_prompt = getSystemPrompt(additional_system_prompt)
        
        if user_summary:
            system_prompt += f"\n\nContext from previous sessions:\n{user_summary}"

        # Combine all messages
        full_conversation_history = [
            {"role": "system", "content": system_prompt}
        ] + messages

        token_count = count_tokens_in_messages(full_conversation_history, model)
        print(f"Total input tokens: {token_count}")

        # Send to OpenAI
        openai_response = client.chat.completions.create(
            model= model
            , messages=full_conversation_history
            , max_tokens=1024
        )

        # Extract AI response
        return openai_response.choices[0].message.content

    except Exception as e:
        print(f"AI Response Generation Error: {e}")
        return "I'm sorry, but I'm having trouble generating a response right now."

def getSystemPrompt(additionalSystemMessage = ""):
    # Base system prompt
    base_system_prompt = (
        "You are a deeply reflective and insightful assistant designed to serve as a journaling guide and therapist. "
        "Your role is to help users explore their emotions, gain self-awareness, challenge their thinking, and take meaningful steps forward. "
        "Your responses should feel natural, conversational, and engaging. Primarily speak in paragraphs. "
        "Use formatting sparingly and only when it helps organize key takeaways."
    )

    return base_system_prompt + "\n\n" + additionalSystemMessage

def getPastMessages(past_sessions):
    # Convert all past session messages into OpenAI format
    formatted_past_messages = []
    
    for past_session in past_sessions:
        past_messages = json.loads(past_session.messages)
    
        if past_session.timestamp.tzinfo is None:
            past_session_timestamp = past_session.timestamp.replace(tzinfo=timezone.utc)
        else:
            past_session_timestamp = past_session.timestamp

        # Compute time difference
        time_difference = datetime.now(timezone.utc) - past_session_timestamp
        
        # Convert time difference to human-readable form
        hours_ago = time_difference.total_seconds() / 3600
    
        if hours_ago < 24:
            time_label = f"{int(hours_ago)} hours ago"
        else:
            time_label = f"{int(hours_ago // 24)} days ago"

        # Add context to user messages only from past sessions
        for msg in past_messages:
            if msg["role"] == "user":
                formatted_past_messages.append({
                    "role": msg["role"],
                    "content": f"[{time_label}, Previous Session ID {past_session.id}] {msg['content']}"
                })
            else:
                formatted_past_messages.append(msg)

    return formatted_past_messages;

def getCurrentMessages(current_session_messages, current_message):# Prepare current session messages
    formatted_current_messages = [
        {
            "role": msg["role"],
            "content": f"[Current Session] {msg['content']}" if msg["role"] == "user" else msg["content"]
        }
        for msg in current_session_messages
    ]

    # Append the new user message if it exists
    if current_message:
        formatted_current_messages.append({"role": "user", "content": f"[Current Session] {current_message}"})

    return formatted_current_messages;


def count_tokens_in_messages(messages, model="gpt-4o-mini"):
    """
    Count the number of tokens in a list of messages.
    Each message is expected to be a dict with 'role' and 'content' keys.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        
        num_tokens = 0
        for message in messages:
            # Every message follows <im_start>{role/name}\n{content}<im_end>\n
            num_tokens += 4
            for key, value in message.items():
                num_tokens += len(encoding.encode(str(value)))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens
    except Exception as e:
        print(f"Error counting tokens: {e}")
        return 0

def generateSummary(messages):
    """
    Generate a summary of the current session and combine it with previous summaries.
    Returns both the session summary and combined summary if there's previous history.
    """
    try:
        # Format messages for the summarization prompt
        formatted_messages = [
            {"role": "system", "content": (
                "You are a summarization assistant. Create a brief, relevant summary of this therapy session. "
                "Focus on key themes, insights, and emotional patterns. "
                "Keep the summary concise but include important context for future reference."
            )},
            {"role": "user", "content": f"Please summarize this therapy session:\n\n" + "\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in messages
            ])}
        ]

        # Generate summary using OpenAI
        summary_response = client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            max_tokens=256
        )

        return summary_response.choices[0].message.content

    except Exception as e:
        print(f"Summary Generation Error: {e}")
        raise

def combineSummaries(historical_summary, new_summary):
    """
    Combine historical summary with new session summary.
    """
    try:
        combined_messages = [
            {"role": "system", "content": (
                "You are a summarization assistant. Create a condensed summary combining the historical "
                "summary with the new session summary. Focus on key patterns, progress, and important context. "
                "Keep the final summary concise but comprehensive."
            )},
            {"role": "user", "content": f"Historical summary:\n{historical_summary}\n\nNew session summary:\n{new_summary}"}
        ]

        combined_response = client.chat.completions.create(
            model=model,
            messages=combined_messages,
            max_tokens=512
        )

        return combined_response.choices[0].message.content

    except Exception as e:
        print(f"Summary Combination Error: {e}")
        raise