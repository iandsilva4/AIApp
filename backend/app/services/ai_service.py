import openai
from app.models.chat_session import ChatSession
from app.models.user_summary import UserSummary
import json
from datetime import datetime, timezone
from config import Config
from flask import request
import numpy as np
from tiktoken import encoding_for_model
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging


logger = logging.getLogger(__name__)

client = openai
client.api_key = Config.OPENAI_API_KEY
model = "gpt-4o-mini"


def generate_ai_response(messages, user_email):
    """
    Generate an AI response using session summaries instead of full chat logs.
    """
    try:
        logger.info(f"[User: {user_email}] Generating AI response with context management.")

        if not messages:  # Handle empty messages case
            latest_message = "User has started a new session."
        else:
            latest_message = messages[-1]['content']

        # Step 1: Get relevant summaries & full conversations
        session_summaries, full_conversations = get_most_relevant_context(user_email, latest_message)

        # Step 2: Set max token budget (adjust based on model)
        MAX_TOKENS = 30000 

        system_prompt = getSystemPrompt()

        # Step 3: Estimate token usage
        total_tokens = count_tokens(system_prompt)

        # Step 4: Create lists for structured message ordering
        system_messages = [{"role": "system", "content": system_prompt}]
        current_session_messages = []
        past_summaries = []
        past_full_conversations = []

        # Step 5: Append only the most recent user-assistant exchanges (current session)
        trimmed_messages = messages #messages[-8:]  # Use last 8 messages for better recency
        for msg in trimmed_messages:
            message_tokens = count_tokens(msg["content"])
            if total_tokens + message_tokens < MAX_TOKENS:
                current_session_messages.append({"role": msg["role"], "content": msg["content"]})
                total_tokens += message_tokens
            else:
                break  # Stop adding messages if we hit the limit

        # Step 6: Add past session summaries (if space allows)
        if session_summaries and total_tokens < MAX_TOKENS * 0.8:  # Leave buffer for current messages
            summaries_text = "\n".join([f"- Session {s['session_id']} ({s['timestamp']}): {s['summary']}" for s in session_summaries])
            summary_tokens = count_tokens(summaries_text)
            if total_tokens + summary_tokens < MAX_TOKENS:
                past_summaries.append({"role": "system", "content": "PAST SUMMARIES:\n" + summaries_text})
                total_tokens += summary_tokens


        # Step 7: If we still have space, include only the **most relevant full conversation**
        if full_conversations and total_tokens < MAX_TOKENS * 0.9:  # Allow buffer for response
            selected_full_convo = full_conversations[0]  # Pick the most relevant one
            full_convo_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in selected_full_convo])
            full_convo_tokens = count_tokens(full_convo_text)
            if total_tokens + full_convo_tokens < MAX_TOKENS:
                # Flatten full_conversations to prevent list nesting
                if isinstance(selected_full_convo, list):
                    full_convo_text = "\n".join([f"{m['role'].capitalize()}: {m['content']}" for m in selected_full_convo])
                else:
                    full_convo_text = str(selected_full_convo)  # Ensure it's a string

                past_full_conversations.append({"role": "system", "content": "FULL PAST CONVERSATION:\n" + full_convo_text})

                total_tokens += full_convo_tokens

        # Step 8: Assemble messages in correct order (system → past context → current session)
        #messages_list = system_messages + past_summaries + past_full_conversations + current_session_messages 
        messages_list = system_messages + past_summaries + current_session_messages # take out full past conversations
        if not current_session_messages:
            messages_list.append({
                "role": "system", 
                "content": "This is a new session. Say hello!"
            })

        # Ensure all messages are properly structured as dictionaries
        if any(isinstance(msg['content'], list) for msg in messages_list):
            logger.error(f"[User: {user_email}] Invalid data format in messages_list: {messages_list}")
            return "Error: Messages are not correctly formatted."

        # Step 8: Generate AI response
        openai_response = client.chat.completions.create(
            model=model,
            messages=messages_list,
            max_tokens=2048  # Response size limit
        )


        return openai_response.choices[0].message.content

    except Exception as e:
        logger.error(f"[User: {user_email}] Error generating AI response: {str(e)}")
        return "I'm having trouble generating a response right now."

def getSystemPrompt():
    # Base system prompt
    base_system_prompt = (
        "You are a reflective and engaging thought partner, helping users explore emotions, challenge their thinking, and take meaningful steps forward. "
        "Prioritize self-discovery over solutions—ask exploratory questions first, help users clarify their thoughts, and only offer guidance when they seem ready. "
        "Use past session context naturally, avoiding unnecessary repetition or summarization. "
        "Ensure questions are open-ended, avoiding leading language or assumed answers. "
        "Maintain a warm, conversational tone—be concise, engaging, and push for deeper reflection when needed."
        "The provided context is structured as follows:\n"
        "- PAST SUMMARIES: Summaries of previous sessions.\n"
        "- FULL CONVERSATIONS: Full logs from previous relevant conversations.\n"
        "- CURRENT MESSAGES: The ongoing discussion."
        "In FULL CONVERSATIONS and CURRENT MESSAGES, you (the system) are the Assistant and you are responding to the User."
    )

    return base_system_prompt

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

def count_tokens(text, model="gpt-4o-mini"):
    """
    Count the number of tokens in a given text.
    """
    try:
        encoding = encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        logger.error(f"Token counting error: {e}")
        return 0
    
def generateSessionSummary(messages):
    """
    Generate a summary of the current session.
    """
    try:
        # Format messages for the summarization prompt
        system_prompt = (
            "You are an AI assistant summarizing a user's journaling session. "
            "Your job is to extract the most important themes and insights. "
            "Summarize in a concise and meaningful way, avoiding unnecessary details. "
        )

        formatted_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Summarize this conversation:\n\n" + "\n".join(
                [f"{msg['role'].capitalize()}: {msg['content']}" for msg in messages]
            )}
        ]
        # Generate summary using OpenAI
        summary_response = client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            #max_tokens=256
        )

        return summary_response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Session Summary Generation Error: {e}")
        raise

def generateUserSummary(session_summaries):
    """
    Generate an overall user summary based on multiple session summaries.
    """
    try:
        logger.info("Generating user summary from session summaries")
        
        user_summary_system_prompt = (
            "You are an assistant that extracts the most important ongoing themes and patterns from multiple therapy sessions. "
            "Your goal is NOT to create a generic summary, but to capture the user's evolving concerns, progress, and emotional patterns over time. "
            "Identify shifts in thinking, unresolved issues, and any recurring struggles or breakthroughs. "
            "Ensure that this summary provides the key context necessary for future responses to feel naturally connected to the user's past experiences. "
            "Keep it concise but meaningful, preserving what truly matters for continuity."
        )

        formatted_messages = [
            {"role": "system", "content": user_summary_system_prompt},
            {"role": "user", "content": (
                "Please extract the most important ongoing themes and patterns from these therapy session summaries:\n\n"
                + "\n\n".join(session_summaries)
            )}
        ]
        # Generate combined summary using OpenAI
        summary_response = client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            #max_tokens=512
        )

        return summary_response.choices[0].message.content

    except Exception as e:
        logger.error(f"User Summary Generation Error: {e}")
        raise

def generate_embedding(text):
    """
    Generate an embedding for a given text using OpenAI.
    """
    try:
        response = openai.embeddings.create(
            model="text-embedding-ada-002",  # Use OpenAI's recommended embedding model
            input=text
        )
        return response.data[0].embedding  # Extract the embedding vector
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None
    
def get_most_relevant_context(user_email, current_message, top_n=3):
    """
    Retrieve the most relevant session summaries and, if necessary, their full conversations.
    """
    user_summary = UserSummary.query.filter_by(user_email=user_email).first()

    # 🔍 Debug: Print if user_summary is missing
    if not user_summary:
        logger.warning(f"[User: {user_email}] No UserSummary found in database.")
        return [], []  # Early return to prevent further issues

    # Handle missing session_summaries or session_embeddings
    if not user_summary.session_summaries:
        logger.warning(f"[User: {user_email}] No session summaries found.")
        session_summaries = []
    else:
        session_summaries = user_summary.session_summaries if isinstance(user_summary.session_summaries, list) else json.loads(user_summary.session_summaries)

    if not user_summary.session_embeddings:
        logger.warning(f"[User: {user_email}] No session embeddings found.")
        session_embeddings = {}
    else:
        session_embeddings = user_summary.session_embeddings if isinstance(user_summary.session_embeddings, dict) else json.loads(user_summary.session_embeddings)

    # Generate embedding for the current message
    current_embedding = generate_embedding(current_message)
    if not current_embedding:
        return session_summaries[:top_n], []

    # Compute similarity scores
    similarity_scores = []
    for session in session_summaries:
        session_id = str(session['session_id'])
        if session_id in session_embeddings:
            session_embedding = np.array(session_embeddings[session_id]).reshape(1, -1)
            score = cosine_similarity([current_embedding], session_embedding)[0][0]
            similarity_scores.append((score, session))

    # Sort by relevance and get top-N summaries
    similarity_scores.sort(reverse=True, key=lambda x: x[0])
    top_summaries = [s[1] for s in similarity_scores[:top_n]]

    # Retrieve full conversations for the top summaries
    full_conversations = []
    for session in top_summaries:
        full_session = ChatSession.query.filter_by(id=session["session_id"]).first()
        if full_session:
            full_conversations.append(json.loads(full_session.messages))

    return top_summaries, full_conversations

