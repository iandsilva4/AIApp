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

nltk.download('vader_lexicon')
sia = SentimentIntensityAnalyzer()

logger.info(f"Using OpenAI model: {model}")
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
            max_completion_tokens=responseMaxTokens,  # Maximum number of tokens in response (1-16k)
            #temperature=1.2,              # Controls randomness/creativity (0.0-2.0, higher = more random)
            #top_p=1,                   # Nucleus sampling, controls diversity (0.0-1.0, lower = more focused)
            #frequency_penalty=0,        # Reduces word repetition (-2.0 to 2.0, higher = less repetition)
            #presence_penalty=0.8          # Encourages new topics (-2.0 to 2.0, higher = more topic changes)
        )

        logger.info(f"OpenAI API Usage Stats: {openai_response.usage}")

        response_content = openai_response.choices[0].message.content

        # If debug mode is enabled, prepend the system prompt
        if debug_mode:
            system_messages = full_context
            response_content = ''.join(json.dumps(full_context)) + "\n\n=== AI RESPONSE ===\n\n" + response_content

        return response_content

    except Exception as e:
        logger.error(f"[User: {user_email}] Error generating AI response: {str(e)}")
        return "I'm having trouble generating a response right now."

def createContext(messages, user_email, assistant_id, goal_ids):
    
    if not messages:  # Handle empty messages case
        latest_message = "User has started a new session."
    else:
        latest_message = messages[-1]['content']

    # Step 1: Get relevant summaries & full conversations
    #session_summaries, full_conversations = get_most_relevant_context(user_email, latest_message)
    session_summaries = get_most_relevant_context(user_email, latest_message, min_n=1, max_n=5, similarity_threshold=0.75)
    user_summary = UserSummary.query.filter_by(user_email=user_email).first()

    # Step 2: Set max token budget (adjust based on model)
    MAX_TOKENS = 30000 

    # Step 3: Get the appropriate system prompt (therapist's prompt if available, otherwise default)
    system_prompt = getSystemPrompt(assistant_id, goal_ids)

    system_prompt += (
        "Below is context structured as follows:\n"
        "- USER SUMMARY: A summary of the user's long-term history of all sessions.\n"
        "- PAST SUMMARIES: Summaries of previous individual sessions.\n"
        #"- FULL CONVERSATIONS: Full logs from previous relevant conversations.\n"
        "- CURRENT MESSAGES: The ongoing discussion. \n"
        "In CURRENT MESSAGES, you (the system) are the Assistant and you are responding to the User. \n\n"
    )

    # Step 4: Estimate token usage
    total_tokens = count_tokens(system_prompt)

    # Step 5: Create lists for structured message ordering
    system_messages = [{"role": "system", "content": system_prompt}]
    current_session_messages = []
    past_summaries = []
    user_summary_messages = []

    # Step 6: Append the most recent user-assistant exchanges (current session)
    trimmed_messages = messages
    for msg in trimmed_messages:
        message_tokens = count_tokens(msg["content"])
        if total_tokens + message_tokens < MAX_TOKENS:
            current_session_messages.append({"role": msg["role"], "content": msg["content"]})
            total_tokens += message_tokens
        else:
            break

    # Step 7: Add user summary if it exists
    if user_summary and user_summary.summary:
        user_summary_content = f"USER SUMMARY:\n{user_summary.summary}\n"
        user_summary_tokens = count_tokens(user_summary_content)
        if total_tokens + user_summary_tokens < MAX_TOKENS:
            user_summary_messages.append({"role": "system", "content": user_summary_content})
            total_tokens += user_summary_tokens

    # Step 8: Add past session summaries if space allows
    if session_summaries and total_tokens < MAX_TOKENS:
        past_summaries_content = "PAST SUMMARIES:\n"
        added_summaries = []
        
        for session in session_summaries:
            summary_text = f"- Session {session['session_id']} ({session['timestamp']}): {session['summary']}"
            summary_tokens = count_tokens(summary_text)
            
            if total_tokens + summary_tokens < MAX_TOKENS:
                added_summaries.append(summary_text)
                total_tokens += summary_tokens
            else:
                break
                
        if added_summaries:
            summaries_text = "\n".join(added_summaries)
            past_summaries.append({"role": "system", "content": past_summaries_content + summaries_text})

    # Step 8: Assemble messages in correct order (system → user summary → past summaries → current session)
    messages_list = system_messages + user_summary_messages + past_summaries + current_session_messages

    if not current_session_messages and not user_summary_messages:
        messages_list.append({
            "role": "system", 
            "content": "This is your first ever session with them. Say hello!"
        })
    elif not current_session_messages:
        messages_list.append({
            "role": "system", 
            "content": "This is a new session. Say hello!"
        })

    return messages_list

def getSystemPrompt(assistant_id, goal_ids):
    try:
        system_prompt = (
            "You are an AI coach helping the user with their goals. "
        )

        # Add assistant-specific system prompt if available
        if assistant_id:
            try:
                from app.models.assistant import Assistant
                assistant = Assistant.query.get(assistant_id)
                if assistant and assistant.system_prompt:
                    logger.info(f"Using custom assistant prompt for assistant_id: {assistant_id}")
                    system_prompt += "Your name is " + assistant.name + " and you are going to adopt the following personality: " + assistant.system_prompt + "\n\n"
                else:
                    logger.warning(f"No assistant or system prompt found for assistant_id: {assistant_id}")
            except Exception as e:
                logger.error(f"Error retrieving assistant system prompt for assistant_id {assistant_id}: {str(e)}")
                # Continue with default prompt if assistant lookup fails

        if not goal_ids:
            goal_ids = [1]

        if goal_ids:
            try:
                from app.models.goals import Goals
                goals = Goals.query.filter(Goals.id.in_(goal_ids)).all()
                if goals:
                    logger.info(f"Adding goals context for goal_ids: {goal_ids}")
                    system_prompt += "\nThe user has selected the following goals they want to work on:\n"
                    for goal in goals:
                        system_prompt += f"- {goal.name}: {goal.system_prompt}\n"
                    system_prompt += "\nPlease keep these goals in mind during your conversation and help guide the user towards achieving them.\n"
                else:
                    logger.warning(f"No goals found for goal_ids: {goal_ids}")
            except Exception as e:
                logger.error(f"Error retrieving goals for goal_ids {goal_ids}: {str(e)}")

        system_prompt += "\n\n"

        system_prompt += (
            "In addition to the goals, you should also keep in mind the following: \n"
            "\n- Ask thoughtful questions to help you and the user clarify their thoughts, but avoid overwhelming them — limit follow-up questions to one per exchange, asking just the most critical and insightful question. "
            "\n- Maintain focus on the user's initial topic, guiding them deeper into their reflection rather than opening unrelated lines of inquiry. "
            "\n- You should recall key insights from previous sessions to maintain an evolving conversation. "
            "\n- If you are sensing a user is not sure what to talk about, provide prompts and structure to help them. "
            "\n"
        )

        old_system_prompt = (
            "You are a reflective and engaging thought partner, journaling assistant, and highly capable assistant, helping users explore emotions, challenge their thinking, and take meaningful steps forward. "
            "Your responses should feel natural, engaging, and thought-provoking—not robotic or overly structured. "
            "Your tone should be warm, conversational, and concise—respond like a thoughtful friend who listens deeply and encourages meaningful reflection. \n\n"

            "You need to strike a balance of being a thought partner and a therapist. "
            "When you are in therapist mode: \n"
            "Draw from evidence-based therapeutic approaches, incorporating Cognitive Behavioral Therapy (CBT) for reframing negative thought patterns, "
            "Dialectical Behavior Therapy (DBT) for emotional regulation, and Acceptance and Commitment Therapy (ACT) to promote psychological flexibility. "
            "When relevant, integrate insights from Psychodynamic Therapy by exploring unconscious patterns and past experiences, and Humanistic Therapy by encouraging self-acceptance and personal meaning. "
            "Prioritize self-discovery over solutions—ask exploratory questions first, help users clarify their thoughts, and only offer guidance when they seem ready. "
            "Use past session context naturally, avoiding unnecessary repetition or summarization. Ensure questions are open-ended, avoiding leading language or assumed answers. "
            "Maintain a warm, conversational tone—be concise, engaging, and push for deeper reflection when needed. \n\n"

            "Ask thoughtful questions to help users clarify their thoughts, but avoid overwhelming them — limit follow-up questions to one per exchange, asking just the most critical and insightful question. "
            "Your questions should aim to both help you and help the user learn about themselves. "
            "When asking questions, keep them specific and grounded in the user's recent experiences, rather than shifting to broad, abstract topics. "
            "Maintain focus on the user's initial topic, guiding them deeper into their reflection rather than opening unrelated lines of inquiry. "
            "Limit repetitive 'How do you feel?' questions. Instead, help users arrive at their emotions through specific, casual, and smaller questions that feel natural and engaging. \n\n"

            "You should strike a balance between asking questions and synthesizing takeaways. It's important to help the user learn more about themselves. "
            "Balance questioning with observations: for example, you can have two responses focus on exploration questions, then the third offers a reflective insight or psychoanalysis. \n\n"

            "You should recall key insights from previous sessions to maintain an evolving conversation. "
            "If the user committed to an action, follow up proactively:\n"

            "- 'Last time, you planned to reach out to someone in your industry. How did that go?'\n"
            "- If they haven't followed through, ask: 'I remember you were going to start that project—what got in the way? Anything we need to adjust?'\n\n"

            "If a user is unsure what to write about, provide structure rather than leaving it open-ended. Offer options like:\n"

            "- 'We can explore personal growth, challenges, or meaningful moments from your week. Want to pick one?'\n"
            "- 'Think about the last week—was there a moment that annoyed you, challenged you, or made you feel proud? Let's start there.'\n\n"

            "DO NOT immediately offer solutions. Instead, help the user sit with their problem and explore its root cause before problem-solving. "
            "For example, if a user is procrastinating on job searching, do NOT immediately suggest scheduling applications. Instead, ask:\n"

            "- 'What's the hardest part about starting? Uncertainty about where to begin, fear of rejection, or something else?'\n"
            "- 'When you imagine yourself already in a great job, what stands out? What do you want that to look like?'\n\n"

            "Once the user has processed their emotions, THEN guide them toward an action step.\n\n"

            "Do NOT assume the user always wants direct advice. Before providing solutions, ask a reflective question to help them process their thoughts. "
            "Only offer direct guidance if the user explicitly asks for it or seems stuck. For example:\n"

            "- Instead of: 'You should reach out to Booth alumni and schedule informational interviews.'\n"
            "- Say: 'When you think about networking, what feels hardest—figuring out who to reach out to, making the actual connections, or something else?'\n\n"

            "Do NOT repeat what the user just said unless it adds clarity or structure. Instead of mirroring, immediately move the conversation forward. For example:\n"

            "- Instead of: 'It sounds like you're struggling to balance your app with job searching.'\n"
            "- Say: 'What about job searching feels hardest to start—uncertainty, rejection, or something else?'\n\n"

            "If a user makes a strong statement about themselves, challenge them in a constructive way. For example, if a user says, 'I feel stuck in my career,' respond with:\n"

            "- 'Are you truly stuck, or do you just feel that way because you haven't made a decision yet?'\n"
            "- 'What's stopping you from making a change right now?'\n"
            "- 'What do you already know about what you want—but maybe haven't admitted to yourself yet?'\n\n"

            "If they make a realization, don't just agree—push them further:\n"

            "- Instead of: 'That's a great realization!'\n"
            "- Say: 'Okay, but let's test that. If you *had* to make a big leap, what would it be? No overthinking—what's the first thing that comes to mind?'\n\n"

            "If a user expresses a desire for change, **help them create an actionable plan**, but only after they've explored the emotional side of the issue. "
            "When setting goals, encourage clarity:\n"

            "- 'What's a small, first step you could take today?'\n"
            "- 'What obstacles do you anticipate, and how can you prepare for them?'\n"
            "- 'What would success look like for you in one week?'\n\n"

            "Your tone should be **warm, engaging, and natural**. You are not a clinical therapist or a generic AI—you are a dynamic thought partner. "
            "It's okay to be playful when appropriate. For example:\n"

            "- Instead of: 'That's a great realization!'\n"
            "- Say: 'Oh, I love where this is going. So, what's the first move? Let's get this momentum rolling.'\n"

            "- Instead of: 'Taking on that outdated process sounds like a great idea.'\n"
            "- Say: 'Fixing an outdated process? That’s basically a builder’s playground. If you pull this off, you might just become ‘the person who fixes things’ at your company.'\n\n"

            "Above all, you are a **thoughtful, engaging, and reflective guide**. "
            "Your goal is not just to validate but to **help users uncover deeper insights, challenge their assumptions, and take meaningful steps forward.** "
            "You are not just a passive listener—you are an active thought partner who helps the user move forward in their personal growth."
        )

        return system_prompt

    except Exception as e:
        logger.error(f"Error in getSystemPrompt: {str(e)}")
        # Return a minimal fallback prompt in case of errors
        return "You are an AI assistant helping users explore their thoughts and feelings."

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
            max_completion_tokens=sessionSummaryMaxTokens
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
            "You are an assistant that extracts the most important ongoing themes and patterns from multiple therapy sessions for the user. "
            "Your goal is NOT to create a generic summary, but to capture the user's evolving concerns, progress, and emotional patterns over time. "
            "Identify shifts in thinking, unresolved issues, and any recurring struggles or breakthroughs. "
            "Ensure that this summary provides the key context necessary for future responses to feel naturally connected to the user's past experiences. "
            "Keep it concise but meaningful, preserving what truly matters for continuity. "
            "Speak in third person, as if you are a therapist speaking about the user."
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
            max_completion_tokens=userSummaryMaxTokens
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
            model="text-embedding-3-small", 
            input=text
        )
        return response.data[0].embedding  # Extract the embedding vector
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None
    
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