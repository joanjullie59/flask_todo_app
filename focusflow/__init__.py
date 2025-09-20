import os
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
from focusflow.extensions import db, start_scheduler, mail
from focusflow.routes import main
from focusflow.models import User
from flask_migrate import Migrate, stamp
from flask_wtf import CSRFProtect
import firebase_admin
from firebase_admin import credentials

csrf = CSRFProtect()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    load_dotenv()  # load environment variables from .env file in development
    app = Flask(__name__)
    
    # Load config from a config.py or environment as needed
    from focusflow.config import Config
    app.config.from_object(Config)
    
    # Create instance folder if missing
    os.makedirs(app.instance_path, exist_ok=True)
    
    # Initialize Firebase Admin with credentials from environment variables
    if not firebase_admin._apps:
        service_account_info = {
            "type": os.getenv("FIREBASE_TYPE"),
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n") if os.getenv("FIREBASE_PRIVATE_KEY") else None,
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
            "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
        }
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)
    
    # Initialize Flask extensions
    mail.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'  # Redirect unauthorized users to login
    csrf.init_app(app)
    
    # Register blueprints
    app.register_blueprint(main)
    
    # Initialize database tables - FIXED VERSION
    with app.app_context():
        try:
            # Create all tables first
            db.create_all()
            print("Database tables created successfully!")
            
            # Then stamp the database with the latest migration version
            # This tells Alembic that the database is up to date
            stamp()
            print("Migration state synchronized!")
            
        except Exception as e:
            print(f"Database initialization error: {e}")
            # If stamping fails, just ensure tables exist
            try:
                db.create_all()
                print("Database tables created as fallback!")
            except Exception as fallback_error:
                print(f"Fallback table creation failed: {fallback_error}")
    
    # Start any scheduler tasks
    start_scheduler(app)
    
    return app

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
