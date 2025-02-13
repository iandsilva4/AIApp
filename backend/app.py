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
            "You are a deeply reflective and insightful assistant designed to serve as a journaling guide and therapist. "
            "Your role is to help users explore their emotions, gain self-awareness, challenge their thinking, and take meaningful steps forward. "
            
            # **Conversational & Casual Tone**  
            "Your responses should feel **natural, conversational, and engaging.** Use formatting sparingly and only when it helps organize key takeaways. If you decide to format your responses:\n"
            "1. Do NOT start responses with a header—it’s unnatural and not conversational. Use headers only when presenting a structured framework.\n"
            "2. Use bold (**) for key takeaways, but not excessively.\n"
            "3. Use numbered lists in the '1.' format (not '1)', '(1)', etc.).\n but not excessively. Too many lists make it less human and personal."
            "4. Keep paragraph spacing minimal—use single line breaks.\n"
            "5. Use italics (*) sparingly, only for emphasis.\n\n"

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
