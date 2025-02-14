from flask import Blueprint, request, jsonify
from app.models.chat_session import ChatSession
from app.models.user_summary import UserSummary
from app.services.ai_service import generate_ai_response, generateSessionSummary, generateUserSummary, generate_embedding
from app.utils.decorators import authenticate
from app.__init__ import db
import json
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='')


@chat_bp.route('/sessions', methods=['GET'])
@authenticate
def get_sessions(user_email):
    try:
        logger.info(f"[User: {user_email}] Received request to get sessions")
        sessions = ChatSession.query.filter_by(
            user_email=user_email,
            is_deleted=False
        ).order_by(ChatSession.timestamp.desc()).all()
        return jsonify([s.to_dict() for s in sessions]), 200
    
    except Exception as e:
        logger.error(f"[User: {user_email}] Session Retrieval Error: {e}")
        return jsonify({"error": "Failed to load sessions"}), 500

@chat_bp.route('/sessions', methods=['POST'])
@authenticate
def create_session(user_email):
    try:
        logger.info(f"[User: {user_email}] Received request to create new session")
        data = request.json
        title = data.get("title", "Untitled Chat").strip()
        
        if not title:
            return jsonify({"error": "Session title cannot be empty"}), 400

        # End previous active sessions
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

        # Generate AI response
        ai_message = generate_ai_response(
            messages=[],
            user_email=user_email
        )

        # Save AI's first message
        initial_messages = [{"role": "assistant", "content": ai_message}]
        session.messages = json.dumps(initial_messages)
        db.session.commit()

        logger.info(f"[User: {user_email}] Successfully created new session with ID: {session.id}")
        return jsonify(session.to_dict()), 201
    
    except Exception as e:
        logger.error(f"[User: {user_email}] Session Creation Error: {e}")
        return jsonify({"error": "Failed to create session"}), 500

@chat_bp.route('/sessions/<int:session_id>', methods=['PUT'])
@authenticate
def update_session(user_email, session_id):
    try:
        logger.info(f"[User: {user_email}] Received request to update session {session_id}")
        data = request.get_json()
        title = data.get('title')
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        session.title = title
        db.session.commit()
        
        return jsonify(session.to_dict())

    except Exception as e:
        logger.error(f"[User: {user_email}] Error updating session: {str(e)}")
        return jsonify({'error': 'Failed to update session'}), 500

@chat_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
@authenticate
def delete_session(user_email, session_id):
    try:
        logger.info(f"[User: {user_email}] Received request to delete session {session_id}")
        session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        if not session.is_ended:
            end_session(user_email, session_id)

        session.is_deleted = True
        session.is_archived = True
        session.is_ended = True

        db.session.commit()
        
        return jsonify({'message': 'Session deleted successfully'})

    except Exception as e:
        logger.error(f"[User: {user_email}] Error deleting session: {str(e)}")
        return jsonify({'error': 'Failed to delete session'}), 500

@chat_bp.route('/sessions/<int:session_id>/archive', methods=['PUT'])
@authenticate
def toggle_archive_session(user_email, session_id):
    try:
        logger.info(f"[User: {user_email}] Received request to toggle archive for session {session_id}")
        session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        # Generate summary from messages
        messages = json.loads(session.messages)
        if not session.summary:
            session.summary = generateSessionSummary(messages)
        if not session.embedding and session.summary:
            # Generate embedding for this summary
            embedding = generate_embedding(session.summary)
            session.embedding = json.dumps(embedding) if embedding else None  # Only store if valid
            
        #switch status
        session.is_archived = not session.is_archived
        db.session.commit()

        # Update user summary after session ends
        update_user_summary(user_email)
        
        return jsonify(session.to_dict())

    except Exception as e:
        logger.error(f"[User: {user_email}] Error archiving session: {str(e)}")
        return jsonify({'error': 'Failed to archive session'}), 500

@chat_bp.route('/sessions/<int:session_id>/end', methods=['PUT'])
@authenticate
def end_session(user_email, session_id):
    try:
        logger.info(f"[User: {user_email}] Received request to end session {session_id}")
        session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        # Generate summary from messages
        messages = json.loads(session.messages)
        session.summary = generateSessionSummary(messages)

        # Generate embedding for this summary
        session.embedding = json.dumps(generate_embedding(session.summary))

        # Mark session as ended
        session.is_ended = True
        db.session.commit()

        logger.info(f"[User: {user_email}] Successfully ended session {session_id} and generated summaries")

        # Update user summary after session ends
        update_user_summary(user_email)
        
        return jsonify({
            **session.to_dict(),
            'session_summary': session.summary
        })

    except Exception as e:
        logger.error(f"[User: {user_email}] Error ending session: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to end session'}), 500

@chat_bp.route('/sessions/<int:session_id>', methods=['GET'])
@authenticate
def get_session_messages(user_email, session_id):
    # Fetch the session
    session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
    if not session:
        return jsonify({"error": "Session not found"}), 404

    # Return the session messages
    try:
        messages = json.loads(session.messages)
        return jsonify({
            "session_id": session.id, 
            "messages": messages, 
            "title": session.title
        }), 200
    except Exception as e:
        logger.error(f"Error loading session: {e}")
        return jsonify({"error": "Failed to load session"}), 500

@chat_bp.route('/chat/respond', methods=['POST'])
@authenticate
def chat_with_ai(user_email):
    try:
        logger.info(f"[User: {user_email}] Received request to chat with AI")
        data = request.json
        session_id = data.get("session_id")
        message = data.get("message")

        if not session_id or not message:
            return jsonify({"error": "Session ID and message are required"}), 400

        # Get the session
        session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        if session.is_ended:
            return jsonify({"error": "This session has ended. Please create a new session to continue chatting."}), 403

        # Load existing messages
        current_messages = json.loads(session.messages)

        current_messages.append({"role": "user", "content": message})

        # Generate AI response
        ai_response = generate_ai_response(
            messages=current_messages,
            user_email=user_email
        )

        # Update messages
        current_messages.append({"role": "assistant", "content": ai_response})

        # Save updated messages
        session.messages = json.dumps(current_messages)
        db.session.commit()

        logger.info(f"[User: {user_email}] Successfully got response from AI for session {session_id}")
        return jsonify({"message": ai_response}), 200

    except Exception as e:
        logger.error(f"[User: {user_email}] AI Error: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to get response from AI"}), 500

def update_session_summaries(session_id, user_email):
    """Generate summary for a specific session"""
    # Get the specific session
    session = ChatSession.query.filter_by(
        id=session_id,
        user_email=user_email,
        is_deleted=False
    ).first()

    if session and not session.summary:
        messages = json.loads(session.messages)
        session.summary = generateSessionSummary(messages)
        
    return session.summary if session else None

def update_user_summary(user_email):
    """
    Update the user's long-term summary after each session.
    """
    try:
        # Get all past session summaries
        all_sessions = ChatSession.query.filter_by(
            user_email=user_email, is_deleted=False, is_archived=False, is_ended=True
        ).order_by(ChatSession.timestamp.desc()).all()

        # Create list of session summaries and embeddings dictionary
        session_summaries = []
        session_embeddings = {}

        for session in all_sessions:
            if session.summary:
                session_summaries.append({
                    'session_id': session.id,
                    'summary': session.summary,
                    'timestamp': session.timestamp.isoformat()
                })
                if session.embedding:  # Store embedding if it exists
                        session_embeddings[str(session.id)] = (
                            json.loads(session.embedding) if isinstance(session.embedding, str) else session.embedding
    )

        if session_summaries:
            # Generate an overall user summary from session summaries
            new_user_summary = generateUserSummary([s['summary'] for s in session_summaries])

            # Update or create user summary in the database
            user_summary = UserSummary.query.filter_by(user_email=user_email).first()
            
            if user_summary:
                user_summary.summary = new_user_summary
                user_summary.session_summaries = json.dumps(session_summaries)
                user_summary.session_embeddings = json.dumps(session_embeddings)
                user_summary.updated_at = datetime.now(timezone.utc)
            else:
                new_user_summary_record = UserSummary(
                    user_email=user_email,
                    summary=new_user_summary,
                    session_summaries=json.dumps(session_summaries),
                    session_embeddings=json.dumps(session_embeddings)
                )
                db.session.add(new_user_summary_record)

            db.session.commit()

    except Exception as e:
        logger.error(f"User Summary Update Error: {e}")

            