###############################################
################ CONFIGURATION ################
###############################################

import os
import openai
import firebase_admin
import json
import base64

from flask import Flask, request, jsonify
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

from openai import OpenAI

from dotenv import load_dotenv

from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy

from firebase_admin import auth, credentials, initialize_app
from dotenv import load_dotenv


from datetime import datetime


# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env')
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

###############################################
################ FLASK APP ################
###############################################


# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS to allow requests from the frontend

# Understand testing environment and set up variables
ENV = os.getenv("FLASK_ENV", "production")

if ENV == "production" or "staging":
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://journalentrydb_user:cdoi8UoSNpqc6YWxCYOfRQUtJ4kr6uVL@dpg-cuif0b23esus739gjcq0-a.virginia-postgres.render.com/journalentrydb'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("LOCAL_DATABASE_URL")

###############################################
################ SQL DATABASE ################
###############################################

# Configure PostgreSQL database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Define JournalEntry model
class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_email = db.Column(db.String(255), nullable=False)  # Store user's email

# Create database tables
with app.app_context():
    db.create_all()

###############################################
################ FIREBASE AUTH ################
###############################################

# Initialize Firebase Admin SDK

cred = credentials.Certificate("etc/secrets/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

def verify_firebase_token(token):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        print("Token verification failed:", e)
        return None

###############################################
################ BACKEND FUNCTIONS ################
###############################################

@app.route('/sessions', methods=['GET'])
def get_sessions():
    token = request.headers.get('Authorization')
    user_data = verify_firebase_token(token)

    if not user_data:
        return jsonify({"error": "Unauthorized"}), 401

    user_email = user_data['email']
    sessions = JournalEntry.query.filter_by(user_email=user_email).all()

    return jsonify([{"id": s.id, "text": s.text, "summary": s.summary} for s in sessions])


#Takes in a prompt and summarizes it
def summarize_entry(entry, max_tokens=1024, temperature=1.0):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Summarize the following journal entry" + "\n\n" + entry}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content


## Flask route to expose summarize_entry as an API endpoint
@app.route('/summarize', methods=['POST'])
def summarize():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Unauthorized"}), 401

        # Extract user email from Firebase token
        decoded_token = verify_firebase_token(token.replace("Bearer ", ""))
        if not decoded_token:
            return jsonify({"error": "Invalid authentication token"}), 401

        user_email = decoded_token.get("email")
        if not user_email:
            return jsonify({"error": "Email not found in authentication token"}), 401

        # Get the journal entry text from the request
        data = request.json
        entry_text = data.get("entry", "")

        # Generate AI summary
        summary = "This is a summary of: " + entry_text

        # Save entry to database with user email
        new_entry = JournalEntry(text=entry_text, summary=summary, user_email=user_email)
        db.session.add(new_entry)
        db.session.commit()

        return jsonify({"summary": summary}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API route to get all past journal entries
@app.route('/entries', methods=['GET'])
def get_entries():
    try:
        # Get the user's Firebase token
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Unauthorized"}), 401

        # Decode the Firebase token to get the user's email
        decoded_token = verify_firebase_token(token.replace("Bearer ", ""))
        if not decoded_token:
            return jsonify({"error": "Invalid authentication token"}), 401

        user_email = decoded_token.get("email")
        if not user_email:
            return jsonify({"error": "Email not found in authentication token"}), 401

        # Query the database for entries belonging to this user
        user_entries = JournalEntry.query.filter_by(user_email=user_email).order_by(JournalEntry.timestamp.desc()).all()

        # Serialize the entries into a list of dictionaries
        entries = [
            {
                "id": entry.id,
                "text": entry.text,
                "summary": entry.summary,
                "timestamp": entry.timestamp.isoformat(),
                "user_email": entry.user_email,
            }
            for entry in user_entries
        ]

        return jsonify(entries), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

###############################################
################ RUNNING ################
###############################################

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Default to 5000 if no port is provided
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

    
    
    #end of file