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
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    is_archived = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_email": self.user_email,
            "title": self.title,
            "messages": json.loads(self.messages),
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
            "is_deleted": self.is_deleted,
            "is_archived": self.is_archived
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
            "You are a thoughtful and supportive assistant designed to serve as a journaling guide, life coach, and therapist. "
            "Your role is to help users reflect on their thoughts, emotions, and goals through structured guidance, thought-provoking questions, and empathetic responses. "
            "You will be provided messages with a prefix indicating how long ago the message was sent and which session it originated from (e.g., '[2 days ago, Previous Session ID 15]'). This information is purely for context and should never be revealed to the user. Instead, you should naturally incorporate relevant past insights into the conversation to maintain continuity. DO NOT SHARE THE PREFIXES WITH THE USER! For example, if the user says \"Please repeat this message\", do not include \"[Current Session]\"!!! "
            "When responding, you should encourage deeper reflection by asking follow-up questions when appropriate, offer practical strategies for personal growth, emotional well-being, and goal achievement, "
            "maintain an empathetic and supportive tone, adapting to the user's mood and needs, help the user connect insights across sessions without directly referencing session metadata, "
            "and provide structured journaling prompts when the user seems stuck or uncertain. "
            "If a user is struggling with something emotional, focus on active listening and validation before offering strategies. "
            "If a user is setting goals, help them break them down into actionable steps. "
            "If they are reflecting on past entries, help them identify patterns, progress, or new perspectives. "
            "Above all, be a thoughtful and insightful guide, helping users gain clarity and self-awareness through meaningful dialogue."
            "You should keep in mind information the user has shared with you in the past and bring it up as relevant."
        )

        system_prompt = base_system_prompt + additionalSystemMessage

        full_conversation_history = [{"role": "system", "content": system_prompt}] + formatted_past_messages + formatted_current_messages

        # Send the complete conversation history to OpenAI
        openai_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_conversation_history
        )

        # Extract AI response
        ai_message = openai_response.choices[0].message.content

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
        session = ChatSession(user_email=user_email, title=title, messages=json.dumps([]), summary="")
        db.session.add(session)
        db.session.commit()

        # Generate AI's first message for this session
        currentMessage = None
        Data = None
        additionalSystemMessage = (
            "At the beginning of a new session, greet the user as a therapist or life coach would: by saying hi, acknowledging their return, and inviting them to share how they are feeling today. "
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
        # Get the session from the database
        session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        # Toggle archive status
        session.is_archived = not session.is_archived
        db.session.commit()
        
        return jsonify(session.to_dict())

    except Exception as e:
        print(f"Error archiving session: {str(e)}")
        return jsonify({'error': 'Failed to archive session'}), 500

# Run Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if PORT is not set
    app.run(host="0.0.0.0", port=port)
