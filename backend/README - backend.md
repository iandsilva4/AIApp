AI Journaling App - Backend

This repository contains the backend for an AI-powered journaling app built with Flask, SQLAlchemy, Firebase Authentication, and OpenAI's GPT-4 API.

Project Structure

📂 app/
├── 📂 models/            # Database models (ORM classes)
│   ├── chat_session.py   # Defines the ChatSession table in the database
│
├── 📂 routes/            # API route handlers (Flask Blueprints)
│   ├── chat_routes.py    # Handles chat session creation, retrieval, updates, and AI interaction
│
├── 📂 services/          # Service layer for AI and authentication
│   ├── ai_service.py     # Calls OpenAI API to generate responses
│   ├── auth_service.py   # Handles Firebase authentication token verification
│
├── 📂 utils/             # Utility functions and decorators
│   ├── decorators.py     # Authentication decorator for protected routes
│
├── __init__.py           # Initializes Flask app, database, and Firebase
├── app.py                # Entry point that runs the Flask app
├── config.py             # Configuration settings (database, API keys, etc.)

File Breakdown & Relationships

1. app.py (Entry Point)

Loads the Flask app by calling create_app() from __init__.py.

Runs the app on the specified port.

2. __init__.py (App Initialization)

Creates the Flask app instance.

Loads configuration settings from config.py.

Initializes Flask extensions (SQLAlchemy, Migrate, CORS, Firebase authentication).

Registers API routes (chat_routes.py).

3. config.py (Configuration Settings)

Loads environment variables (e.g., DATABASE_URL, OPENAI_API_KEY).

Provides configuration settings to the app via Config class.

4. models/chat_session.py (Database Model)

Defines the ChatSession table using SQLAlchemy.

Stores chat messages, timestamps, session metadata (deleted, archived, ended status).

Provides a to_dict() method for API responses.

5. routes/chat_routes.py (Chat Session API)

Implements API endpoints:

POST /sessions → Create a new chat session.

GET /sessions → Retrieve user’s chat sessions.

GET /sessions/<session_id> → Fetch messages from a specific session.

POST /chat/respond → Send user message & get AI response.

PUT /sessions/<session_id> → Update session title.

DELETE /sessions/<session_id> → Soft delete a session.

PUT /sessions/<session_id>/archive → Archive/unarchive a session.

PUT /sessions/<session_id>/end → Mark session as ended.

Uses @authenticate to ensure requests are from authenticated users.

Calls generate_ai_response() from ai_service.py when a user sends a message.

6. services/ai_service.py (AI Response Handling)

Calls OpenAI’s GPT-4 API to generate AI responses based on user messages.

Formats past session messages and includes them as context for better responses.

Saves AI responses in the database (ChatSession.messages).

7. services/auth_service.py (User Authentication)

Verifies Firebase Authentication tokens.

Ensures only authenticated users can access protected routes.

8. utils/decorators.py (Authentication Middleware)

Defines @authenticate, a decorator that:

Extracts the Firebase Auth token from request headers.

Calls verify_firebase_token() from auth_service.py.

Passes the user’s email to the protected route function.

How Everything Connects

User makes an API request (e.g., POST /sessions).

authenticate decorator verifies the user’s Firebase token.

Request is routed through chat_routes.py, which:

Interacts with ChatSession (via SQLAlchemy) to manage chat data.

Calls generate_ai_response() when AI input is needed.

ai_service.py sends chat history to OpenAI and returns a response.

Response is saved to the database and returned to the user.

Setup & Running Locally

1. Install Dependencies

pip install -r requirements.txt

2. Set Environment Variables

Create a .env file:

DATABASE_URL=postgresql://username:password@localhost:5432/yourdatabase
OPENAI_API_KEY=sk-...
FIREBASE_CREDENTIALS=serviceAccountKey.json

3. Initialize Database

flask db upgrade  # Apply database migrations

4. Run the Flask App

flask run

Next Steps

Want to improve error handling?

Need help debugging database queries?

Looking to add more AI features?

