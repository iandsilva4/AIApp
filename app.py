import os
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS to allow requests from the frontend

# Configure PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://journalentrydb_user:cdoi8UoSNpqc6YWxCYOfRQUtJ4kr6uVL@dpg-cuif0b23esus739gjcq0-a.virginia-postgres.render.com/journalentrydb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)

# Define JournalEntry model
class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create database tables
with app.app_context():
    db.create_all()

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
        # Get JSON data from the request
        data = request.json
        entry = data.get("entry", "")
        max_tokens = data.get("max_tokens", 1024)
        temperature = data.get("temperature", 1.0)

        # Generate summary using OpenAI
        summary = summarize_entry(entry, max_tokens, temperature)

        # Save the journal entry and summary to the database
        new_entry = JournalEntry(text=entry, summary=summary)
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({"summary": summary}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API route to get all past journal entries
@app.route('/entries', methods=['GET'])
def get_entries():
    entries = JournalEntry.query.order_by(JournalEntry.timestamp.desc()).all()
    return jsonify([
        {"id": e.id, "text": e.text, "summary": e.summary, "timestamp": e.timestamp.isoformat()}
        for e in entries
    ])

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Default to 5000 if no port is provided
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

    
