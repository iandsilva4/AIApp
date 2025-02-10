import os
import openai
import json
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from firebase_admin import auth, credentials, initialize_app
from datetime import datetime
from dotenv import load_dotenv

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
class ChatSessionv1(db.Model):
    __tablename__ = "chat_sessionv1"
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(255), nullable=False, default="Untitled Chat")
    messages = db.Column(db.Text, nullable=False, default="[]")
    summary = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_email": self.user_email,
            "title": self.title,
            "messages": json.loads(self.messages),
            "summary": self.summary,
            "timestamp": self.timestamp.isoformat(),
        }

# Firebase token verification
def verify_firebase_token(token):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        print(f"Firebase Token Error: {e}")
        return None


################################
## INITIALIZATION
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
        session = ChatSessionv1(user_email=user_email, title=title, messages=json.dumps([]), summary="")
        db.session.add(session)
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
        sessions = ChatSessionv1.query.filter_by(user_email=user_email).order_by(ChatSessionv1.timestamp.desc()).all()
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
    session = ChatSessionv1.query.filter_by(id=session_id, user_email=user_email).first()
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

    session = ChatSessionv1.query.filter_by(id=session_id, user_email=user_email).first()
    if not session:
        return jsonify({"error": "Session not found"}), 404

    try:
        # Send the user message to OpenAI
        openai_response = client.chat.completions.create(
        model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": message}]
        )

        # Extract the assistant's response
        ai_message = openai_response.choices[0].message.content

        # Update the session with the new message
        messages = json.loads(session.messages)
        messages.append({"role": "user", "content": message})
        messages.append({"role": "assistant", "content": ai_message})
        session.messages = json.dumps(messages)
        db.session.commit()

        return jsonify({"message": ai_message}), 200
    
    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({"error": "Failed to get response from AI"}), 500


# Run Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if PORT is not set
    app.run(host="0.0.0.0", port=port)
