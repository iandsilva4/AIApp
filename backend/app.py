import os
import openai
import json
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from firebase_admin import auth, credentials, initialize_app
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from firebase_admin import firestore
from functools import wraps

################################
## INITIALIZATION
################################

# Load environment variables
load_dotenv()

# Initialize OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai
client.api_key = OPENAI_API_KEY

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database and migration
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_app = initialize_app(cred)

# Database model
class ChatSession(db.Model):
    __tablename__ = "chat_sessionv1"
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(255), nullable=False, default="Untitled Chat")
    messages = db.Column(db.Text, nullable=False, default="[]")
    summary = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)
    is_ended = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_email": self.user_email,
            "title": self.title,
            "messages": json.loads(self.messages),
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
            "is_deleted": self.is_deleted,
            "is_archived": self.is_archived,
            "is_ended": self.is_ended
        }

# Firebase token verification
def verify_firebase_token(token):
    try:
        # Add clock tolerance when verifying the token
        decoded_token = auth.verify_id_token(
            token,
            check_revoked=True,
            clock_skew_seconds=30
        )
        return decoded_token
    except auth.RevokedIdTokenError:
        return None
    except auth.InvalidIdTokenError:
        return None
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return None

# Add this near the top with other decorators
def authenticate(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Unauthorized"}), 401

        user_data = verify_firebase_token(token.replace("Bearer ", ""))
        if not user_data:
            return jsonify({"error": "Unauthorized"}), 401

        return f(user_data['email'], *args, **kwargs)
    return decorated_function

################################
## Functions
################################

def generate_ai_response(user_email, session_id, current_message=None, data=None, additionalSystemMessage = ""):
    """Generates an AI response based on past session context and an optional current message."""

    session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()

    data = request.json
    session_id = data.get("session_id")
    message = data.get("message")

    try:
        # Load existing messages from this session
        current_session_messages = json.loads(session.messages)

        # Fetch all previous sessions (excluding archived and deleted ones)
        past_sessions = ChatSession.query.filter(
            ChatSession.user_email == user_email,
            ChatSession.id != session_id,
            ChatSession.is_deleted == False,
            ChatSession.is_archived == False
        ).order_by(ChatSession.timestamp.desc()).all()

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
                    formatted_past_messages.append(msg)  # Keep AI messages unchanged

        # Prepare current session messages (only adding '[Current Session]' for user messages)
        formatted_current_messages = [
            {
                "role": msg["role"],
                "content": f"[Current Session] {msg['content']}" if msg["role"] == "user" else msg["content"]
            }
            for msg in current_session_messages
        ]

        # Append the new user message
        formatted_current_messages.append({"role": "user", "content": f"[Current Session] {message}"})

        # Combine past and current session messages
        
        base_system_prompt = (
            "You are a deeply reflective and insightful assistant designed to serve as a journaling guide, life coach, and thought partner, often acting like an extremely capable therapist. "
            "Your role is to help users explore their emotions, gain self-awareness, challenge their thinking, and make meaningful progress in their personal growth. "
            
            # **Formatting Guidelines**  
            "When formatting your responses:\n"
            "1. Do NOT start responses with a header—it’s unnatural and not conversational. Use headers only sparingly when presenting a strong framework.\n"
            "2. Use bold (**) for key takeaways and structured insights, but not excessively.\n"
            "3. For lists, always add a blank line before the list starts.\n"
            "4. For numbered lists, use '1.' format (not '1)', '(1)', etc.).\n"
            "5. Keep paragraph spacing minimal – use single line breaks.\n"
            "6. Use italics (*) sparingly, only for emphasis.\n\n"

            # **Session Continuity & Proactive Accountability**  
            "You will be provided messages with a prefix indicating when they were sent and which session they originated from "
            "(e.g., '[2 days ago, Previous Session ID 15]'). This is for context only. NEVER repeat this prefix to the user—it would confuse them. "
            "However, you should absolutely use previous information to maintain an evolving, continuous conversation. "
            "NEVER expose session metadata. If the user references past discussions, recall specific insights from previous sessions in a natural way.\n\n"

            "Hold the user accountable for past commitments without waiting for them to bring them up. If they said they would take action, follow up directly:\n"
            
            "- Instead of: 'Have you been making progress?'\n"
            "- Say: 'Last time, you committed to reaching out to someone in your industry. How did that go? What insights did you gain from the conversation?'\n\n"

            "If they haven’t followed through, don’t shame them—help them troubleshoot:\n"
            
            "- 'I remember you planned to start building that side project last week. What got in the way? Anything we need to adjust?'\n\n"

            # **Helping Directionless Users Find Focus**  
            "If a user seems unsure about what to journal about, provide structure rather than leaving it fully open-ended. "
            "For example, if they say they don’t know what to write about, respond with:\n"
            
            "- 'We can explore a few areas—personal growth, challenges, or meaningful moments from your week. Want to pick one?' \n"
            "- 'Think about the last week—was there a moment that annoyed you, challenged you, or made you feel proud? Let’s start there.' \n"
            
            "If they remain uncertain, offer a choice of structured prompts:\n"
            
            "- 'Would you like to reflect on a recent challenge, a moment of joy, or something that’s been on your mind?' \n\n"

            # **Conversational Style & Deeper Engagement**  
            "Your responses should feel **genuine, thought-provoking, and human** – NOT like a generic chatbot. "
            "Avoid excessive validation (e.g., 'That’s a great insight') and instead **challenge the user’s thinking in a constructive way**. "
            "Be natural and conversational. If appropriate, inject warmth and lightness into the discussion. "
            
            "Use follow-up questions that build on what the user actually said, rather than just moving to the next generic reflection question. "
            "If a user expresses frustration or uncertainty, don’t just validate—help them break it down further. "
            "For example, if a user says they feel restless in their career, DO NOT simply ask what they want next. Instead, push their thinking:\n"

            "- 'You mentioned restlessness—does that feel more like boredom, frustration, or something else?'\n"
            "- 'What would need to change in your work to make you feel more energized?'\n"
            "- 'Is this a feeling that’s only showing up in your career, or do you feel it in other parts of your life too?'\n\n"

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
            "If a user expresses a desire for change, **help them create an actionable plan**. "
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

            # **Journaling Prompts for When Users Feel Stuck**  
            "If a user seems unsure or lost in their reflections, **offer structured journaling prompts** to help them explore their thoughts. "
            "For example:\n"

            "- 'Write about a moment in the past week that stood out to you. Why do you think it stuck with you?'\n"
            "- 'Describe your current emotions as if they were weather. What does today feel like – sunny, stormy, foggy?'\n"
            "- 'If you could give advice to yourself from one year ago, what would you say?'\n\n"

            # **Overall Mission**  
            "Above all, you are a **thoughtful, deeply engaging, and reflective guide**. "
            "Your goal is not just to validate but to **help users uncover deeper insights, challenge their assumptions, and take meaningful steps forward.** "
            "You are not just a passive listener—you are an active thought partner who helps the user move forward in their personal growth. "
        )





        system_prompt = base_system_prompt + additionalSystemMessage

        full_conversation_history = [{"role": "system", "content": system_prompt}] + formatted_past_messages + formatted_current_messages

        # Send the complete conversation history to OpenAI
        openai_response = client.chat.completions.create(
            model="gpt-4o-mini",
            #model="gpt-4o",
            messages=full_conversation_history
        )

        # Extract AI response
        ai_message = openai_response.choices[0].message.content

        #print(json.dumps(full_conversation_history, indent=4))

        return ai_message

    except Exception as e:
        print(f"AI Response Generation Error: {e}")
        return "I'm sorry, but I'm having trouble generating a response right now."

################################
## API ROUTES
################################


# Route to create a new session
@app.route('/sessions', methods=['POST'])
def create_session():
    token = request.headers.get('Authorization') # it gets the token from teh metadata sent from the HTTP request
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    user_data = verify_firebase_token(token.replace("Bearer ", ""))
    if not user_data:
        return jsonify({"error": "Unauthorized"}), 401

    user_email = user_data['email']
    data = request.json
    
    title = data.get("title", "Untitled Chat").strip()
    if not title:
        return jsonify({"error": "Session title cannot be empty"}), 400

    try:
        # End the previous active session if it exists
        active_sessions = ChatSession.query.filter_by(
            user_email=user_email,
            is_deleted=False,
            is_archived=False,
            is_ended=False
        ).all()
        
        for session in active_sessions:
            session.is_ended = True
        
        # Create new session
        session = ChatSession(user_email=user_email, title=title, messages=json.dumps([]), summary="")
        db.session.add(session)
        db.session.commit()

        # Generate AI's first message for this session
        currentMessage = None
        Data = None
        additionalSystemMessage = (
            "When starting a new session, greet the user with a simple, professional welcome like 'Hello! How can I help you today?' ALWAYS start with Hello! or a similar entry greeting"
            "You should create a welcoming and supportive environment, allowing the user to set the direction of the conversation. "
            "If relevant, you may gently reference past discussions, but do so naturally rather than immediately bringing up past topics. "
            "Your goal is to establish an open, reflective space where the user feels encouraged to share their thoughts and emotions."
        )
        ai_message = generate_ai_response(user_email, session.id, currentMessage, currentMessage, additionalSystemMessage)

        # Save AI's first message in the session
        initial_messages = [{"role": "assistant", "content": ai_message}]
        session.messages = json.dumps(initial_messages)
        db.session.commit()

        return jsonify(session.to_dict()), 201
    
    except Exception as e:
        print(f"Session Creation Error: {e}")
        return jsonify({"error": "Failed to create session"}), 500

# Route to retrieve all sessions for a user
@app.route('/sessions', methods=['GET'])
def get_sessions():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    user_data = verify_firebase_token(token.replace("Bearer ", ""))
    if not user_data:
        return jsonify({"error": "Unauthorized"}), 401

    user_email = user_data['email']

    try:
        sessions = ChatSession.query.filter_by(
            user_email=user_email,
            is_deleted=False  # Only get non-deleted sessions
        ).order_by(ChatSession.timestamp.desc()).all()
        return jsonify([s.to_dict() for s in sessions]), 200
    
    except Exception as e:
        print(f"Session Retrieval Error: {e}")
        return jsonify({"error": "Failed to load sessions"}), 500

@app.route('/sessions/<int:session_id>', methods=['GET'])
def get_session_messages(session_id):
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    user_data = verify_firebase_token(token.replace("Bearer ", ""))
    if not user_data:
        return jsonify({"error": "Unauthorized"}), 401

    user_email = user_data['email']

    # Fetch the session
    session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Return the session messages
    try:
        messages = json.loads(session.messages)
        return jsonify({"session_id": session.id, "messages": messages, "title": session.title}), 200
    except Exception as e:
        print(f"Error loading session: {e}")
        return jsonify({"error": "Failed to load session"}), 500

# Route to handle user input and AI response
@app.route('/chat/respond', methods=['POST'])
def chat_with_ai():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Unauthorized"}), 401

    user_data = verify_firebase_token(token.replace("Bearer ", ""))
    if not user_data:
        return jsonify({"error": "Unauthorized"}), 401

    user_email = user_data['email']
    data = request.json
    session_id = data.get("session_id")
    message = data.get("message")

    if not session_id or not message:
        return jsonify({"error": "Session ID and message are required"}), 400

    session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    if session.is_ended:
        return jsonify({"error": "This session has ended. Please create a new session to continue chatting."}), 403

    try:
        # Load existing messages from this session
        current_session_messages = json.loads(session.messages)

        additionalSystemMessage = ""
        ai_response = generate_ai_response(user_email, session_id, data, additionalSystemMessage)

        # Append AI response to the current session
        current_session_messages.append({"role": "user", "content": message})
        current_session_messages.append({"role": "assistant", "content": ai_response})

        # Save updated messages to the session
        session.messages = json.dumps(current_session_messages)
        db.session.commit()

        return jsonify({"message": ai_response}), 200

    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({"error": "Failed to get response from AI"}), 500

# Replace the existing update endpoint with this one
@app.route('/sessions/<int:session_id>', methods=['PUT'])
@authenticate
def update_session(user_email, session_id):
    try:
        data = request.get_json()
        title = data.get('title')
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        # Get the session from the database
        session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        # Update the session title
        session.title = title
        db.session.commit()
        
        return jsonify(session.to_dict())

    except Exception as e:
        print(f"Error updating session: {str(e)}")
        return jsonify({'error': 'Failed to update session'}), 500

@app.route('/sessions/<int:session_id>', methods=['DELETE'])
@authenticate
def delete_session(user_email, session_id):
    try:
        # Get the session from the database
        session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        # Soft delete the session
        session.is_deleted = True
        db.session.commit()
        
        return jsonify({'message': 'Session deleted successfully'})

    except Exception as e:
        print(f"Error deleting session: {str(e)}")
        return jsonify({'error': 'Failed to delete session'}), 500

# Add new archive endpoint
@app.route('/sessions/<int:session_id>/archive', methods=['PUT'])
@authenticate
def toggle_archive_session(user_email, session_id):
    try:
        session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        session.is_archived = not session.is_archived
        if session.is_archived:
            session.is_ended = True
        
        db.session.commit()
        
        return jsonify(session.to_dict())

    except Exception as e:
        print(f"Error archiving session: {str(e)}")
        return jsonify({'error': 'Failed to archive session'}), 500

# Add new end session endpoint
@app.route('/sessions/<int:session_id>/end', methods=['PUT'])
@authenticate
def end_session(user_email, session_id):
    try:
        session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        session.is_ended = True
        db.session.commit()
        
        return jsonify(session.to_dict())

    except Exception as e:
        print(f"Error ending session: {str(e)}")
        return jsonify({'error': 'Failed to end session'}), 500

# Run Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if PORT is not set
    app.run(host="0.0.0.0", port=port, debug=True)
