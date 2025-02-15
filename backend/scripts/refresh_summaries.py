import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.__init__ import create_app, db
from app.models.chat_session import ChatSession
from app.models.user_summary import UserSummary
from app.services.ai_service import (
    generateSessionSummary,
    generateUserSummary,
    generate_embedding
)
from flask import current_app
import json
import logging
import argparse
from datetime import datetime
from sqlalchemy import text
from app.routes.chat_routes import update_user_summary  # Add this import at the top

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_session_filter_preferences():
    """Get user preferences for which types of sessions to include"""
    print("\nSession Filter Options:")
    include_ended = input("Include ended sessions? (y/n): ").lower() == 'y'
    include_archived = input("Include archived sessions? (y/n): ").lower() == 'y'
    include_deleted = input("Include soft-deleted sessions? (y/n): ").lower() == 'y'
    
    # Ask for specific filters
    specific_session = input("\nEnter specific session ID (or press Enter to skip): ").strip()
    specific_user = input("Enter specific user email (or press Enter to skip): ").strip()
    
    return {
        'include_ended': include_ended,
        'include_archived': include_archived,
        'include_deleted': include_deleted,
        'session_id': int(specific_session) if specific_session.isdigit() else None,
        'user_email': specific_user if specific_user else None
    }

def get_filtered_sessions(preferences):
    """Get sessions based on filter preferences"""
    query = ChatSession.query
    
    # Build query based on preferences
    conditions = []
    
    if not preferences['include_ended']:
        conditions.append(ChatSession.is_ended == False)
    
    if not preferences['include_archived']:
        conditions.append(ChatSession.is_archived == False)
        
    if not preferences['include_deleted']:
        conditions.append(ChatSession.is_deleted == False)
        
    # Add specific session filter
    if preferences.get('session_id'):
        conditions.append(ChatSession.id == preferences['session_id'])
        
    # Add specific user filter
    if preferences.get('user_email'):
        conditions.append(ChatSession.user_email == preferences['user_email'])
    
    # Apply all conditions
    for condition in conditions:
        query = query.filter(condition)
    
    # Order by id ascending
    query = query.order_by(ChatSession.id.asc())
    
    return query.all()

def refresh_session_summaries(filter_preferences=None):
    """Refresh all session summaries"""
    logger.info("Starting session summaries refresh...")
    
    if filter_preferences is None:
        filter_preferences = get_session_filter_preferences()
    
    sessions = get_filtered_sessions(filter_preferences)
    count = 0
    
    logger.info(f"Found {len(sessions)} sessions matching filter criteria")
    
    for session in sessions:
        try:
            messages = json.loads(session.messages)
            new_summary = generateSessionSummary(messages)
            session.summary = new_summary
            
            # Generate new embedding for the summary
            new_embedding = generate_embedding(new_summary)
            session.embedding = json.dumps(new_embedding)
            
            db.session.add(session)
            db.session.commit()
            count += 1
            logger.info(f"Updated summary for session {session.id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating session {session.id}: {str(e)}")

    refresh_user_summaries(filter_preferences)
    
    logger.info(f"Completed refreshing {count} session summaries")
    return count, filter_preferences

def refresh_user_summaries(filter_preferences=None):
    """Refresh all user summaries"""
    logger.info("Starting user summaries refresh...")
    
    # Get unique user emails from user summary table
    # Get unique user emails from user summary table, filtered by preferences if specified
    query = db.session.query(UserSummary.user_email.distinct())
    if filter_preferences and filter_preferences.get('user_email'):
        query = query.filter(UserSummary.user_email == filter_preferences['user_email'])
    user_emails = query.all()
    count = 0
    
    for (user_email,) in user_emails:  # Unpack the tuple from the query
        try:
            # Use existing update_user_summary function
            update_user_summary(user_email)
            count += 1
            logger.info(f"Updated summary for user {user_email}")
            
        except Exception as e:
            logger.error(f"Error updating user {user_email}: {str(e)}")
    
    logger.info(f"Completed refreshing {count} user summaries")
    return count

def refresh_embeddings(filter_preferences=None):
    """Refresh all session embeddings"""
    logger.info("Starting embeddings refresh...")
    
    # Get all sessions based on filters
    query = ChatSession.query
    if filter_preferences:
        if not filter_preferences['include_ended']:
            query = query.filter(ChatSession.ended == False)
        if not filter_preferences['include_archived']:
            query = query.filter(ChatSession.archived == False)
        if not filter_preferences['include_deleted']:
            query = query.filter(ChatSession.deleted == False)
    
    sessions = query.all()
    count = 0
    
    logger.info(f"Found {len(sessions)} sessions to process")
    
    for session in sessions:
        try:
            if not session.summary:
                logger.warning(f"Skipping session {session.id} - no summary found")
                continue
            
            # Generate embedding for session summary
            embedding = generate_embedding(session.summary)
            if embedding:
                session.embedding = json.dumps(embedding)
                db.session.add(session)
                db.session.commit()
                count += 1
                logger.info(f"Updated embedding for session {session.id}")
            else:
                logger.warning(f"Failed to generate embedding for session {session.id}")
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating embedding for session {session.id}: {str(e)}")

    refresh_user_summaries(filter_preferences)
    
    logger.info(f"Completed refreshing embeddings for {count} sessions")
    return count

def delete_marked_chats():
    """Permanently remove chats marked as deleted from the database"""
    logger.info("Starting permanent deletion of marked chats...")
    count = 0
    
    try:
        # Get count of deleted sessions first
        deleted_count = ChatSession.query.filter_by(is_deleted=True).count()
        logger.info(f"Found {deleted_count} deleted sessions")
        
        if deleted_count == 0:
            logger.info("No deleted sessions found")
            return 0
        
        # Get table name from model
        table_name = ChatSession.__table__.name
        
        # Use SQL delete with text() function and dynamic table name
        result = db.session.execute(
            text(f"DELETE FROM {table_name} WHERE is_deleted = true")
        )
        count = result.rowcount
        
        # Commit the changes
        db.session.commit()
        
        # Verify deletion
        remaining = ChatSession.query.filter_by(is_deleted=True).count()
        logger.info(f"Remaining deleted sessions after cleanup: {remaining}")
        
        logger.info(f"Successfully deleted {count} sessions")
        return count
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during deletion process: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Refresh AI-generated content')
    parser.add_argument('--sessions', action='store_true', help='Refresh session summaries')
    parser.add_argument('--users', action='store_true', help='Refresh user summaries')
    parser.add_argument('--embeddings', action='store_true', help='Refresh embeddings')
    parser.add_argument('--all', action='store_true', help='Refresh everything')
    parser.add_argument('--no-prompt', action='store_true', help='Skip prompts and include all sessions')
    parser.add_argument('--delete-marked', action='store_true', help='Permanently delete marked chats')
    
    args = parser.parse_args()
    
    app = create_app()
    with app.app_context():
        # Get filter preferences if needed
        filter_preferences = get_session_filter_preferences()
        
        try:
            if args.delete_marked:
                deleted_count = delete_marked_chats()
                logger.info(f"Permanently deleted {deleted_count} marked chats")
            
            if args.all or args.sessions:
                session_count, filter_preferences = refresh_session_summaries(filter_preferences)
                logger.info(f"Updated {session_count} session summaries")

            if args.embeddings:
                embedding_count = refresh_embeddings(filter_preferences)
                logger.info(f"Updated embeddings for {embedding_count} sessions")
                
            if args.users:
                user_count = refresh_user_summaries(filter_preferences)
                logger.info(f"Updated {user_count} user summaries")

                
        except Exception as e:
            logger.error(f"An error occurred during refresh: {str(e)}")
            raise

if __name__ == "__main__":
    main() 