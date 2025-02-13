from flask import Blueprint, request, jsonify
from app.models.chat_session import ChatSession
from app.models.user_summary import UserSummary
from app.services.ai_service import generate_ai_response, generateSummary, combineSummaries, getSystemPrompt
from app.utils.decorators import authenticate
from app.__init__ import db
import json
from datetime import datetime, timezone

chat_bp = Blueprint('chat', __name__, url_prefix='')


@chat_bp.route('/sessions', methods=['GET'])
@authenticate
def get_sessions(user_email):
    try:
        sessions = ChatSession.query.filter_by(
            user_email=user_email,
            is_deleted=False
        ).order_by(ChatSession.timestamp.desc()).all()
        return jsonify([s.to_dict() for s in sessions]), 200
    
    except Exception as e:
        print(f"Session Retrieval Error: {e}")
        return jsonify({"error": "Failed to load sessions"}), 500

@chat_bp.route('/sessions', methods=['POST'])
@authenticate
def create_session(user_email):
    data = request.json
    title = data.get("title", "Untitled Chat").strip()
    
    if not title:
        return jsonify({"error": "Session title cannot be empty"}), 400

    try:
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

        return jsonify(session.to_dict()), 201
    
    except Exception as e:
        print(f"Session Creation Error: {e}")
        return jsonify({"error": "Failed to create session"}), 500

@chat_bp.route('/sessions/<int:session_id>', methods=['PUT'])
@authenticate
def update_session(user_email, session_id):
    try:
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
        print(f"Error updating session: {str(e)}")
        return jsonify({'error': 'Failed to update session'}), 500

@chat_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
@authenticate
def delete_session(user_email, session_id):
    try:
        session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        session.is_deleted = True
        db.session.commit()
        
        return jsonify({'message': 'Session deleted successfully'})

    except Exception as e:
        print(f"Error deleting session: {str(e)}")
        return jsonify({'error': 'Failed to delete session'}), 500

@chat_bp.route('/sessions/<int:session_id>/archive', methods=['PUT'])
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

@chat_bp.route('/sessions/<int:session_id>/end', methods=['PUT'])
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
        print(f"Error loading session: {e}")
        return jsonify({"error": "Failed to load session"}), 500

@chat_bp.route('/chat/respond', methods=['POST'])
@authenticate
def chat_with_ai(user_email):
    data = request.json
    session_id = data.get("session_id")
    message = data.get("message")

    if not session_id or not message:
        return jsonify({"error": "Session ID and message are required"}), 400

    try:
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

        # Get system prompt
        additional_system_prompt = getSystemPrompt("")  # You'll need to move this function to ai_service.py

        # Generate AI response
        ai_response = generate_ai_response(
            messages=current_messages,
            additional_system_prompt=additional_system_prompt,
            user_summary=summary_text
        )

        # Update messages
        current_messages.append({"role": "user", "content": message})
        current_messages.append({"role": "assistant", "content": ai_response})

        # Save updated messages
        session.messages = json.dumps(current_messages)
        db.session.commit()

        return jsonify({"message": ai_response}), 200

    except Exception as e:
        print(f"AI Error: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to get response from AI"}), 500

@chat_bp.route('/sessions/<session_id>/summary', methods=['POST'])
@authenticate
def create_session_summary(user_email, session_id):
    try:
        # Get the current session
        session = ChatSession.query.filter_by(id=session_id, user_email=user_email).first()
        if not session:
            return jsonify({"error": "Session not found"}), 404

        # Load current session messages
        current_messages = json.loads(session.messages)
        
        # Generate new summary
        new_summary = generateSummary(current_messages)
        
        # Get existing summary if it exists
        existing_summary = UserSummary.query.filter_by(user_email=user_email).first()
        
        if existing_summary:
            # Combine with existing summary
            combined_summary = combineSummaries(existing_summary.summary, new_summary)
            existing_summary.summary = combined_summary
            existing_summary.updated_at = datetime.now(timezone.utc)
        else:
            # Create new summary record
            new_summary_record = UserSummary(user_email=user_email, summary=new_summary)
            db.session.add(new_summary_record)

        db.session.commit()
        return jsonify({
            "message": "Summary generated successfully",
            "summary": existing_summary.summary if existing_summary else new_summary
        }), 200
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

