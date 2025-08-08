import openai
import os
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
import openai
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Add debug flag from environment
debug_mode = str(os.getenv("DEBUG_MODE", "false")).lower() == "true"

logger = logging.getLogger(__name__)

client = openai
client.api_key = Config.OPENAI_API_KEY
model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
secondary_model = os.getenv("OPENAI_MODEL_SECONDARY", "gpt-4o-mini")

nltk.download('vader_lexicon')
sia = SentimentIntensityAnalyzer()

logger.info(f"Using OpenAI model: {model}")
logger.info(f"Using Secondary OpenAI model: {secondary_model}")

# Embedding model should match stored vector dimension (existing data is 1536 dims)
embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
logger.info(f"Using Embedding model: {embedding_model}")

sessionSummaryMaxTokens = 2048
userSummaryMaxTokens = 2048
responseMaxTokens = 1024

def generate_ai_response(messages, user_email, assistant_id=None, goal_ids=None):
    """
    Generate an AI response using session summaries instead of full chat logs.
    """
    try:
        logger.info(f"[User: {user_email}] Generating AI response with context management.")

        full_context = createContext(messages, user_email, assistant_id, goal_ids)

        # Step 9: Generate AI response
        openai_response = client.chat.completions.create(
            model=model,
            messages=full_context,
            #max_completion_tokens=responseMaxTokens,  # Maximum number of tokens in response (1-16k)
            #temperature=1.2,              # Controls randomness/creativity (0.0-2.0, higher = more random)
            #top_p=1,                   # Nucleus sampling, controls diversity (0.0-1.0, lower = more focused)
            #frequency_penalty=0,        # Reduces word repetition (-2.0 to 2.0, higher = less repetition)
            #presence_penalty=0.8          # Encourages new topics (-2.0 to 2.0, higher = more topic changes)
        )

        logger.info(f"OpenAI API Usage Stats (Main AI Response): {openai_response.usage}")

        response_content = openai_response.choices[0].message.content

        # If debug mode is enabled, prepend the system prompt
        if debug_mode:
            logger.info(''.join(json.dumps(full_context)) + "\n\n=== AI RESPONSE ===\n\n" + response_content)

        return response_content

    except Exception as e:
        logger.error(f"[User: {user_email}] Error generating AI response: {str(e)}")
        return "I'm having trouble generating a response right now."

def createContext(messages, user_email, assistant_id, goal_ids):
    """
    Builds the full context for an AI response, including relevant past session summaries and user history.
    """
    if not messages:
        latest_message = "User has started a new session."
        # Get recent session context for first message
        recent_context = get_most_recent_session_context(user_email)
    else:
        latest_message = messages[-1]['content']
        recent_context = None

    # Step 1: Fetch relevant past sessions
    user_summary = UserSummary.query.filter_by(user_email=user_email).first()

    # Step 2: Get the updated system prompt
    system_prompt = getSystemPrompt(assistant_id, goal_ids, user_email)

    # Step 5: Organize context structure
    system_messages = [{"role": "system", "content": system_prompt}]

    current_session_messages = []
    past_summaries = []
    user_summary_messages = []

    # Step 6: Include recent user-assistant exchanges (current session)
    for msg in messages:
        current_session_messages.append({"role": msg["role"], "content": msg["content"]})

    # Step 7: Add user summary if available
    if user_summary and user_summary.summary:
        trimmed_summary = trim_user_summary(user_summary.summary, latest_message)
        user_summary_content = f"USER SUMMARY:\n{trimmed_summary}\n"
        user_summary_messages.append({"role": "system", "content": user_summary_content})

    # Step 8: Add recent session context for first message
    if recent_context:
        past_summaries.append({
            "role": "system", 
            "content": f"MOST RECENT SESSION CONTEXT:\n{recent_context}"
        })

    # Step 9: Inject relevant past insights if they apply
    relevant_insights = inject_relevant_past_insights(user_email, latest_message)
    if relevant_insights:
        past_summaries.append({"role": "system", "content": f"**Relevant Past Session Insights:** {relevant_insights}"})

    # Step 10: Assemble full context
    messages_list = system_messages + user_summary_messages + past_summaries + current_session_messages

    if not current_session_messages and not user_summary_messages:
        if recent_context:
            messages_list.append({
                "role": "system", 
                "content": "This is a new session, but you have met them before. Consider the recent context above when greeting them. But be concise in what you say."
            })
        else:
            messages_list.append({
                "role": "system", 
                "content": "This is your first ever session with them. You haven't met them before. Say hello!"
            })
    elif not current_session_messages:
        messages_list.append({"role": "system", "content": "This is a new session. Say hello!"})

    return messages_list

def getSystemPrompt(assistant_id, goal_ids, user_email):
    """
    Generates the system prompt, incorporating user goals, past insights, and follow-up instructions.
    """
    try:
        system_prompt = "You are an AI coach helping the user with their goals."

        # Add assistant-specific system prompt if available
        if assistant_id:
            try:
                from app.models.assistant import Assistant
                assistant = Assistant.query.get(assistant_id)
                if assistant and assistant.system_prompt:
                    logger.info(f"Using custom assistant prompt for assistant_id: {assistant_id}")
                    system_prompt += f"\nYour name is {assistant.name}, and your personality is: {assistant.system_prompt}"
                else:
                    logger.warning(f"No assistant system prompt found for assistant_id: {assistant_id}")
            except Exception as e:
                logger.error(f"Error retrieving assistant system prompt for assistant_id {assistant_id}: {str(e)}")

        # Add user goals
        if goal_ids:
            try:
                from app.models.goals import Goals
                goals = Goals.query.filter(Goals.id.in_(goal_ids)).all()
                if goals:
                    logger.info(f"Adding goals context for goal_ids: {goal_ids}")
                    system_prompt += "\n\nThe user has selected the following goals:\n"
                    for goal in goals:
                        system_prompt += f"- {goal.name}: {goal.system_prompt}\n"
            except Exception as e:
                logger.error(f"Error retrieving goals for goal_ids {goal_ids}: {str(e)}")

        # Add follow-up instructions
        system_prompt += (
            "\n\nYou must recall key insights from previous sessions to maintain an evolving conversation. "
            "Ensure you follow up on recurring themes and past discussions naturally, without forcing repetition."
        )

        return system_prompt

    except Exception as e:
        logger.error(f"Error in getSystemPrompt: {str(e)}")
        return "You are an AI assistant helping users explore their thoughts and feelings."

def trim_user_summary(user_summary, latest_message):
    """
    Trims the user summary to retain only the most relevant themes based on the latest conversation topic.
    Removes details that are less relevant to the user's current focus.
    """
    try:
        prompt = (
            "You are helping an AI coach respond to its user. Here is an overall summary of the user's history. "
            "Can you pull out what you think the AI coach should know when responding to the user?. Remove any outdated or less relevant details.\n\n"
            f"User Summary:\n{user_summary}\n\n"
            f"Latest User Message:\n{latest_message}\n\n"
            "Provide a concise summary of what you think the AI coach should know."
        )

        response = client.chat.completions.create(
            model=secondary_model,
            messages=[{"role": "system", "content": prompt}],
            #max_completion_tokens=300  # Limit to a smaller summary
        )

        logger.info(f"OpenAI API Usage Stats (Trim User Summary): {response.usage}")

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Error trimming user summary: {str(e)}")
        return user_summary  # If error, return original summary

def inject_relevant_past_insights(user_email, latest_message):
    """
    Selects past insights from session summaries (NOT user summary) that are relevant to the user's latest message.
    Limits to the 1-2 most recent relevant insights.
    """
    try:
        # Fetch past session summaries
        past_sessions = get_most_relevant_context(user_email, latest_message, min_n=2, max_n=5, similarity_threshold=0.75)
        if not past_sessions:
            return ""

        # Extract only the most relevant insights
        session_summaries_text = "\n\n".join([s["summary"] for s in past_sessions])

        prompt = (
            "The user has past journaling sessions. Extract only the 1-2 most relevant insights that relate "
            "to the user's latest message. Ignore general themes — only specific takeaways that help in this moment.\n\n"
            "if there is nothing relevant, just say 'No relevant insights found' but only say this if there is really nothing.\n\n"
            "Past Session Summaries:\n"
            f"{session_summaries_text}\n\n"
            "Latest User Message:\n"
            f"{latest_message}\n\n"
            "Provide the most relevant past insights in a concise format. Please refer to the user as the user isntead of 'you'."
        )

        response = client.chat.completions.create(
            model=secondary_model,
            messages=[{"role": "system", "content": prompt},{"role": "user", "content": "Can you please give me a summary of the past sessions?"}],
            #max_completion_tokens=150  # Limit insights to 1-2 takeaways
        )

        logger.info(f"OpenAI API Usage Stats (Past Session Insights): {response.usage}")

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Error Injecting Relevant Past Session Insights: {str(e)}")
        return ""

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
    Generate a structured session summary including key themes, emotions, challenges,
    insights, key personal details, and actionable next steps.
    """
    try:
        system_prompt = (
            "You are summarizing a user's journaling session. "
            "Structure your summary exactly as follows:\n\n"
            "**Key Themes & Emotions:**\n"
            "[Briefly summarize main feelings and topics explored.]\n\n"
            "**Challenges & Patterns:**\n"
            "[Highlight recurring struggles, decision-making patterns, or emotional triggers.]\n\n"
            "**Insights & Reflections:**\n"
            "[Capture new realizations or shifts in the user's perspective.]\n\n"
            "**Key Details Learned:**\n"
            "- [List concrete personal details or life updates explicitly mentioned.]\n\n"
            "**Potential Next Steps:**\n"
            "[Suggest immediate or future actions the user could take.]"
        )

        formatted_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                "Summarize the following conversation:\n\n" +
                "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in messages])
            )}
        ]

        summary_response = client.chat.completions.create(
            model=secondary_model,
            messages=formatted_messages,
            #max_completion_tokens=sessionSummaryMaxTokens
        )

        logger.info(f"OpenAI API Usage Stats (Session Summary): {summary_response.usage}")

        summary = summary_response.choices[0].message.content.strip()

        if not summary:
            logger.warning("Generated summary is empty.")
            return "Summary unavailable. Try refining the session details."

        return summary

    except Exception as e:
        logger.error(f"Session Summary Generation Error: {e}")
        return "An error occurred while generating the summary."

def generate_embedding(text):
    """
    Generate an embedding for a given text using OpenAI.
    """
    try:
        response = openai.embeddings.create(
            model=embedding_model,
            input=text
        )
        return response.data[0].embedding  # Extract the embedding vector
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None

def generateUserSummary(session_summaries, previous_summary=None):
    """
    Generate an evolving user summary by comparing past and current session insights.
    """
    try:
        system_prompt = (
            "You are summarizing a user's long-term growth and evolving thoughts based on multiple journaling sessions. "
            "Ensure that you track how the user's mindset has changed over time rather than repeating the same observations. "
            "Format the summary as follows:\n\n"
            "**Key Themes & Patterns:**\n"
            "[List 3-5 recurring major themes from past sessions.]\n\n"
            "**Recent Changes in Thinking:**\n"
            "[Compare new insights with past user summaries to track shifts in perspective.]\n\n"
            "**Persistent Personal Facts:**\n"
            "- [List key life details mentioned that should be remembered long-term (e.g., names, places, dates, etc.).]\n\n"
            "**Ongoing Focus Areas:**\n"
            "[Suggest what the AI should keep tracking in future conversations.]"
        )

        user_summary_messages = [{"role": "system", "content": system_prompt}]

        # If there's a previous user summary, compare it to the new sessions
        if previous_summary:
            comparison_prompt = (
                "Compare the following past user summary with the new session insights and update only what has changed:\n\n"
                f"PAST SUMMARY:\n{previous_summary}\n\n"
                "NEW SESSION INSIGHTS:\n" + "\n\n".join(session_summaries)
            )
            user_summary_messages.append({"role": "user", "content": comparison_prompt})
        else:
            user_summary_messages.append({"role": "user", "content": "\n\n".join(session_summaries)})
            print("AA#########################")

        # Generate summary
        summary_response = client.chat.completions.create(
            model=secondary_model,
            messages=user_summary_messages,
            #max_completion_tokens=userSummaryMaxTokens
        )

        logger.info(f"OpenAI API Usage Stats (User Summary): {summary_response.usage}")

        summary = summary_response.choices[0].message.content.strip()

        if not summary:
            logger.warning("Generated user summary is empty.")
            logger.warning("Finish reason:", summary_response.choices[0].finish_reason)
            return "Summary unavailable. Try refining the session details."

        return summary

    except Exception as e:
        logger.error(f"User Summary Generation Error: {e}")
        return "An error occurred while generating the user summary."
    
def get_most_relevant_context(user_email, current_message, min_n=2, max_n=5, similarity_threshold=0.7):
    """
    Retrieve the most relevant session summaries and, if necessary, their full conversations.
    Returns min_n to max_n most relevant sessions based on similarity threshold.
    """
    try:
        # Get user summary, return empty list if none exists
        user_summary = UserSummary.query.filter_by(user_email=user_email).first()
        if not user_summary:
            logger.info(f"[User: {user_email}] No UserSummary found - new user.")
            return []

        # Handle missing or empty session_summaries
        if not user_summary.session_summaries:
            logger.info(f"[User: {user_email}] No session summaries found.")
            return []

        # Parse session summaries, handle potential JSON errors
        try:
            session_summaries = (
                user_summary.session_summaries 
                if isinstance(user_summary.session_summaries, list) 
                else json.loads(user_summary.session_summaries)
            )
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"[User: {user_email}] Invalid session_summaries format.")
            return []

        # If no session summaries exist, return empty list
        if not session_summaries:
            return []

        # Handle missing or empty session_embeddings
        if not user_summary.session_embeddings:
            logger.info(f"[User: {user_email}] No session embeddings found.")
            return session_summaries[:min_n]  # Return most recent sessions if no embeddings

        # Parse session embeddings, handle potential JSON errors
        try:
            session_embeddings = (
                user_summary.session_embeddings 
                if isinstance(user_summary.session_embeddings, dict) 
                else json.loads(user_summary.session_embeddings)
            )
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"[User: {user_email}] Invalid session_embeddings format.")
            return session_summaries[:min_n]  # Return most recent sessions if invalid embeddings

        # Generate embedding for current message
        current_embedding = generate_embedding(current_message)
        if not current_embedding:
            logger.warning(f"[User: {user_email}] Could not generate embedding for current message.")
            return session_summaries[:min_n]  # Return most recent sessions if embedding fails

        # Compute similarity scores for valid embeddings
        similarity_scores = []
        for session in session_summaries:
            session_id = str(session['session_id'])
            if session_id in session_embeddings:
                try:
                    session_embedding = np.array(session_embeddings[session_id]).reshape(1, -1)
                    score = cosine_similarity([current_embedding], session_embedding)[0][0]
                    similarity_scores.append((score, session))
                except (ValueError, TypeError):
                    logger.warning(f"[User: {user_email}] Invalid embedding format for session {session_id}")
                    continue

        # If we couldn't compute any similarity scores, return most recent sessions
        if not similarity_scores:
            return session_summaries[:min_n]

        # Sort by relevance (highest to lowest)
        similarity_scores.sort(reverse=True, key=lambda x: x[0])

        # Get minimum required sessions
        relevant_sessions = [s[1] for s in similarity_scores[:min_n]]
        
        # Add additional sessions up to max_n if they meet threshold
        for score, session in similarity_scores[min_n:]:
            if score >= similarity_threshold and len(relevant_sessions) < max_n:
                relevant_sessions.append(session)
        
        # Log included and excluded scores
        included_scores = [f"{score:.3f}" for score, _ in similarity_scores[:len(relevant_sessions)]]
        excluded_scores = [f"{score:.3f}" for score, _ in similarity_scores[len(relevant_sessions):]]
        logger.info(f"[User: {user_email}] Returning {len(relevant_sessions)} relevant sessions "
                   f"(minimum {min_n}, maximum {max_n}, threshold {similarity_threshold}). "
                   f"Included scores: {', '.join(included_scores)}. "
                   f"Excluded scores: {', '.join(excluded_scores) if excluded_scores else 'none'}")
        
        return relevant_sessions

    except Exception as e:
        logger.error(f"[User: {user_email}] Error in get_most_relevant_context: {str(e)}")
        return []  # Return empty list on any error

def analyze_sentiment(text):
    """Analyze sentiment using VADER (for fast analysis)."""
    score = sia.polarity_scores(text)['compound']
    
    if score >= 0.3:
        sentiment = "Positive"
    elif score <= -0.3:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"

    return {"sentiment": sentiment, "sentiment_score": score}

def get_most_recent_session_context(user_email):
    """
    Get a synthesized context from the user's most recent session.
    """
    try:
        # Get the most recent ended session
        recent_session = ChatSession.query.filter_by(
            user_email=user_email,
            is_deleted=False,
            is_archived=False,
            is_ended=True
        ).order_by(ChatSession.timestamp.desc()).first()

        if not recent_session:
            return None

        messages = json.loads(recent_session.messages)
        if not messages:
            return None

        prompt = (
            "Synthesize the key points from this recent conversation to help an AI coach "
            "maintain continuity with the user. Focus on immediate concerns and ongoing topics "
            "that might be relevant to the new conversation they just started.\n\n"
            "Recent Conversation:\n" +
            "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in messages])
        )

        response = client.chat.completions.create(
            model=secondary_model,
            messages=[{"role": "system", "content": prompt}],
            #max_completion_tokens=300
        )

        logger.info(f"OpenAI API Usage Stats (Recent Session Context): {response.usage}")
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Error getting recent session context: {str(e)}")
        return None

