from flask import Blueprint, request, jsonify
from app.models.chat_session import ChatSession
from app.models.user_summary import UserSummary
from app.services.ai_service import generate_ai_response, generateSessionSummary, generateUserSummary
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

        # Generate AI's first message
        additionalSystemMessage = (
            "When starting a new session, greet the user with a simple, professional welcome like 'Hello! How can I help you today?' "
            "ALWAYS start with Hello! or a similar entry greeting"
        )

        # Get user summary if it exists
        user_summary = UserSummary.query.filter_by(user_email=user_email).first()
        summary_text = user_summary.summary if user_summary else None

        # Generate AI response
        ai_message = generate_ai_response(
            messages=[],
            additional_system_prompt=additionalSystemMessage,
            user_summary=summary_text
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

        session.is_deleted = True
        session.is_archived = True
        session.is_ended = True

        update_user_and_session_summaries(user_email)

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

        #switch status
        session.is_archived = not session.is_archived
        
        #if archived, end session and update summaries
        if session.is_archived:
            session.is_ended = True
            update_user_and_session_summaries(user_email)
        
        db.session.commit()
        
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

        # Mark session as ended
        session.is_ended = True

        # Update summaries
        update_user_and_session_summaries(user_email)

        db.session.commit()
        logger.info(f"[User: {user_email}] Successfully ended session {session_id} and generated summaries")
        
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
        
        # Get user summary if it exists
        user_summary = UserSummary.query.filter_by(user_email=user_email).first()
        summary_text = user_summary.summary if user_summary else None
        session_summaries = user_summary.session_summaries if user_summary else None

        # Get system prompt
        additional_system_prompt = ""

        # Generate AI response
        ai_response = generate_ai_response(
            messages=current_messages,
            additional_system_prompt=additional_system_prompt,
            user_summary=summary_text,
            session_summaries=session_summaries
        )

        # Update messages
        current_messages.append({"role": "user", "content": message})
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


def update_user_and_session_summaries(user_email):
    """Update session summaries and overall user summary"""
    # Get all session summaries for this user
    all_sessions = ChatSession.query.filter_by(
        user_email=user_email,
        is_deleted=False,
        is_archived=False,
        is_ended=True
    ).order_by(ChatSession.timestamp.desc()).all()

    # Generate session summaries for any sessions missing them
    for s in all_sessions:
        if not s.summary:
            messages = json.loads(s.messages)
            s.summary = generateSessionSummary(messages)
    
    session_summaries = [s.summary for s in all_sessions if s.summary]
    
    if session_summaries:
        # Generate/update user summary
        user_summary = UserSummary.query.filter_by(user_email=user_email).first()
        new_user_summary = generateUserSummary(session_summaries)
        
        # Create a list of session summary objects with metadata
        session_summary_objects = []
        for s in all_sessions:
            if s.summary:
                session_summary_objects.append({
                    'session_id': s.id,
                    'title': s.title,
                    'timestamp': s.timestamp.isoformat(),
                    'summary': s.summary
                })
        
        if user_summary:
            user_summary.summary = new_user_summary
            user_summary.session_summaries = json.dumps(session_summary_objects)
            user_summary.updated_at = datetime.now(timezone.utc)
        else:
            new_user_summary_record = UserSummary(
                user_email=user_email,
                summary=new_user_summary,
                session_summaries=json.dumps(session_summary_objects)
            )
            db.session.add(new_user_summary_record)