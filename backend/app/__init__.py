from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from firebase_admin import credentials, initialize_app
from config import Config
import logging

# Initialize Flask extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Initialize extensions
    CORS(app)
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize Firebase
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_app = initialize_app(cred)
    
    # Register blueprints
    # Import routes here to avoid circular imports
    # Registers chat_routes.py to handle chat-related API routes.
    from app.routes.chat_routes import chat_bp
    app.register_blueprint(chat_bp)
    
    return app 