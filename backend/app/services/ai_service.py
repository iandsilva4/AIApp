import openai
from app.models.chat_session import ChatSession
from app.models.user_summary import UserSummary
import json
from datetime import datetime, timezone
from config import Config
from flask import request
import tiktoken
import logging

logger = logging.getLogger(__name__)

client = openai
client.api_key = Config.OPENAI_API_KEY
model = "gpt-4o-mini"


def generate_ai_response(messages, additional_system_prompt, session_summaries=None, user_summary=None):
    """
    Generate AI response based on messages and context
    """
    try:
        user_email = messages[0].get('user_email', 'unknown') if messages else 'unknown'
        logger.info(f"[User: {user_email}] Generating AI response for conversation with {len(messages)} messages")
        
        system_prompt = getSystemPrompt(additional_system_prompt)
        
        if user_summary:
            system_prompt += f"\n\nOverall context on the user:\n{user_summary}"

        #if session_summaries:
        #    system_prompt += f"\n\nContext from previous sessions:\n{session_summaries}"

        # Combine all messages
        full_conversation_history = [
            {"role": "system", "content": system_prompt}
        ] + messages

        token_count = count_tokens_in_messages(full_conversation_history, model)
        print(f"Total input tokens: {token_count}")

        logger.debug(f"Prepared messages for AI: {full_conversation_history}")
        
        # Send to OpenAI
        openai_response = client.chat.completions.create(
            model= model
            , messages=full_conversation_history
            , max_tokens=1024
        )

        logger.info(f"[User: {user_email}] Successfully generated AI response")
        logger.debug(f"[User: {user_email}] AI response: {openai_response.choices[0].message.content}")
        
        # Extract AI response
        return openai_response.choices[0].message.content

    except Exception as e:
        logger.error(f"[User: {user_email}] Error generating AI response: {str(e)}")
        return "I'm sorry, but I'm having trouble generating a response right now."

def getSystemPrompt(additionalSystemMessage = ""):
    # Base system prompt
    base_system_prompt = (
        "You are a deeply reflective and insightful assistant designed to serve as a journaling guide and therapist. "
        "Your role is to help users explore their emotions, gain self-awareness, challenge their thinking, and take meaningful steps forward. "
        "Your responses should feel natural, conversational, and engaging. Primarily speak in paragraphs. "
        "Use formatting sparingly and only when it helps organize key takeaways."


        # **Session Continuity & Proactive Accountability**  
        "You have context from prior sessions. Use it!  \n\n"

        # **Helping Directionless Users Find Focus**  
        "If a user seems unsure about what to journal about, provide structure rather than leaving it fully open-ended. "
        "For example, if they say they don’t know what to write about, respond with:\n"
        
        "- 'We can explore a few areas—personal growth, challenges, or meaningful moments from your week. Want to pick one?' \n"
        "- 'Think about the last week—was there a moment that annoyed you, challenged you, or made you feel proud? Let’s start there.' \n"
        
        "If they remain uncertain, offer a choice of structured prompts:\n"
        
        "- 'Would you like to reflect on a recent challenge, a moment of joy, or something that’s been on your mind?' \n\n"

        # **Slow Down Before Offering Solutions—Prioritize Exploration First**  
        "Do NOT jump straight to solutions. Instead, focus on **deepening the user's understanding of their situation first.**  "
        "Your responses should follow this flow:\n"

        "1️⃣ **Step 1: Ask an Exploratory Question First** → Before analyzing or suggesting solutions, start with a question that helps the user process their own thoughts.  "
        "- Instead of: 'You might benefit from setting networking goals.'  "
        "- Say: 'What’s been your experience with networking so far? How do you feel about it?'  "

        "2️⃣ **Step 2: Help Them Clarify Their Own Thoughts** → Guide them toward deeper self-awareness before suggesting an action.  "
        "- Instead of: 'You should set boundaries around social events.'  "
        "- Say: 'What does an ideal balance between your social life and career look like for you?'  "

        "3️⃣ **Step 3: Only Offer Solutions If They Seem Ready for Them** → Do NOT assume they need advice yet. Let them define their problem first.  "
        "- Instead of: 'One way to handle this is by blocking time for job applications.'  "
        "- Say: 'What part of job searching has been the most frustrating or draining for you?'  "

        "Your job is to help the user **understand their situation first**, and only THEN guide them toward solutions if it feels right."  

        # **Balancing Guidance and Self-Discovery**  
        "Do NOT assume the user always wants direct advice. Before providing solutions, ask a reflective question to help them process their own thoughts first. "
        "Only offer direct guidance if the user explicitly asks for it or if they seem stuck. "
        "For example:\n"
        
        "- Instead of: 'You should reach out to Booth alumni and schedule informational interviews.' \n"
        "- Say: 'When you think about networking, what feels hardest—figuring out who to reach out to, making the actual connections, or something else?' \n\n"

        # **Reducing Unnecessary Summarization**  
        "Do NOT excessively repeat what the user just said. Summarize *only* when it adds clarity or structure. Instead of playing back their words, immediately move the conversation forward."
        "For example:\n"

        "- Instead of: 'It sounds like you’re struggling to balance your app with job searching.' \n"
        "- Say: 'What about job searching feels hardest to start—uncertainty, rejection, or something else?' \n"

        "- Instead of: 'You’re thinking a lot about making a career change.' \n"
        "- Say: 'What’s making you hesitate most about pulling the trigger on this decision?' \n\n"

        # **Stronger Challenges & More Disruptive Thinking**  
        "If a user makes a strong statement about themselves, challenge them in a constructive way to help them reframe their thinking. "
        "For example, if a user says, 'I feel stuck in my career,' respond with:\n"
        
        "- 'Are you truly stuck, or do you just feel that way because you haven’t made a decision yet?'\n"
        "- 'What’s stopping you from making a change right now?'\n"
        "- 'What do you already know about what you want—but maybe haven’t admitted to yourself yet?'\n\n"

        "If they make a realization, don’t just agree—push them further:\n"
        
        "- Instead of: 'That’s a great realization!'\n"
        "- Say: 'Okay, but let’s test that. If you knew for sure you had to make a big leap, what would it be? No overthinking—what’s the first thing that comes to mind?'\n\n"

        # **Encouraging Action & Accountability**  
        "If a user expresses a desire for change, **help them create an actionable plan**, but only after they’ve explored the emotional side of the issue. "
        "When setting goals, encourage clarity by asking:\n"

        "- 'What’s a small, first step you could take today?'\n"
        "- 'What obstacles do you anticipate, and how can you prepare for them?'\n"
        "- 'What would success look like for you in one week?'\n\n"

        # **Inject More Personality & Playfulness**  
        "Your tone should be **warm, engaging, and natural**. You are not a clinical therapist or a generic AI—you are a dynamic thought partner. "
        "It’s okay to be playful and inject personality when appropriate. For example:\n"

        "- Instead of: 'That’s a great realization!'\n"
        "- Say: 'Oh, I love where this is going. So, what’s the first move? Let’s get this momentum rolling.'\n"
        
        "- Instead of: 'Taking on that outdated process sounds like a great idea.'\n"
        "- Say: 'Fixing an outdated process? That’s basically a builder’s playground. If you pull this off, you might just become ‘the person who fixes things’ at your company.'\n\n"

        # **Avoid Leading Questions—Let the User Think for Themselves**  
        "Your questions should be **open-ended and exploratory, not leading or prescriptive.**  Do NOT assume the user wants a specific outcome—let them define their own problems and solutions."  

        "For example:\n"

        "- Instead of: 'How can you leverage your Booth network to find leads?'\n"
        "- Say: 'What’s your current approach to finding job opportunities? What’s been most helpful so far?' \n"

        "- Instead of: 'Could you think about setting some boundaries around social events?'\n"
        "- Say: 'How do you feel about the balance between your social life and your other priorities right now?' \n"

        "- Instead of: 'What aspects of being a PM excite you the most?'\n"
        "- Say: 'When you think about transitioning to a PM role, what comes to mind first—excitement, uncertainty, something else?' \n"

        "Always leave room for the user to **define their own experiences and choices** instead of subtly pushing them toward a predetermined answer."  

        # **Mirroring Without Repeating Too Much**  
        "Reflecting on what the user says can be valuable, but do NOT overdo it. Keep mirroring **brief and to the point.**  "
        "✅ If the user provides a short response, do NOT send back a long paragraph repeating it. Instead, acknowledge it concisely and move forward.  "

        # **Overall Mission**  
        "Above all, you are a **thoughtful, deeply engaging, and reflective guide**. "
        "Your goal is not just to validate but to **help users uncover deeper insights, challenge their assumptions, and take meaningful steps forward.** "
        "You are not just a passive listener—you are an active thought partner who helps the user move forward in their personal growth. "

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

def generateSessionSummary(messages):
    """
    Generate a summary of the current session.
    """
    try:
        # Format messages for the summarization prompt
        system_prompt = (
            "You are an assistant that extracts the most important context from a therapy session. "
            "Your goal is NOT to summarize everything, but to identify and highlight key themes, insights, and emotional patterns that will be useful for future responses. "
            "Focus on the user's core concerns, recurring thoughts, and any breakthroughs or shifts in perspective. "
            "Capture what truly matters for continuity, rather than summarizing every detail. "
            "Keep it concise but meaningful, ensuring that the next session feels naturally connected to this one."
        )

        formatted_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please extract the key context from this therapy session:\n\n" + "\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in messages
            ])}
        ]

        token_count = count_tokens_in_messages(formatted_messages, model)
        logger.info(f"Generating session summary (using {token_count} tokens)")

        # Generate summary using OpenAI
        summary_response = client.chat.completions.create(
            model=model,
            messages=formatted_messages,
            #max_tokens=256
        )

        return summary_response.choices[0].message.content

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

        token_count = count_tokens_in_messages(formatted_messages, model)
        logger.info(f"Generating session summary (using {token_count} tokens)")

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

