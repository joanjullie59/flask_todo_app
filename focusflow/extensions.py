from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from flask import current_app
from flask_mail import Mail
import atexit
import logging
from flask_wtf import CSRFProtect

mail = Mail()
db = SQLAlchemy()
scheduler = BackgroundScheduler()
CSRF = CSRFProtect()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_reminders():
    """Check for due reminders and send notifications"""
    try:
        # Get the app instance properly to avoid context issues
        from focusflow import create_app
        app = create_app()
        
        with app.app_context():
            try:
                # Local import to avoid circular import
                from focusflow.models import Todo
                
                # Query for due tasks with active reminders
                due_tasks = Todo.query.filter(
                    Todo.reminder_active == True,
                    Todo.due_date <= datetime.utcnow()
                ).all()
                
                # Process each due task
                for task in due_tasks:
                    logger.info(f"Reminder: Task '{task.content}' is due at {task.due_date}")
                    print(f"Reminder: Task '{task.content}' is due at {task.due_date}")
                    
                    # Optional: Add email notification logic here
                    # send_reminder_email(task)
                    
                    # Optional: Mark reminder as sent to avoid duplicate notifications
                    # task.reminder_sent = True
                    # db.session.commit()
                
                if due_tasks:
                    logger.info(f"Processed {len(due_tasks)} due reminders")
                    
            except Exception as db_error:
                logger.error(f"Database error in check_reminders: {db_error}")
                
    except Exception as e:
        logger.error(f"Scheduler error in check_reminders: {e}")

def send_reminder_email(task):
    """Send email reminder for a due task (optional implementation)"""
    try:
        from flask_mail import Message
        
        # Get user email from the task relationship
        user_email = task.user.email if hasattr(task, 'user') and task.user else None
        
        if user_email:
            msg = Message(
                subject=f"Reminder: {task.content}",
                recipients=[user_email],
                body=f"Your task '{task.content}' was due at {task.due_date}. Don't forget to complete it!"
            )
            mail.send(msg)
            logger.info(f"Reminder email sent to {user_email} for task: {task.content}")
        else:
            logger.warning(f"No user email found for task: {task.content}")
            
    except Exception as e:
        logger.error(f"Error sending reminder email: {e}")

def start_scheduler(app):
    """Initialize and start the background scheduler"""
    try:
        # Only start scheduler if it's not already running
        if not scheduler.running:
            # Add the reminder checking job
            scheduler.add_job(
                func=check_reminders, 
                trigger="interval", 
                minutes=1,  # Check every minute - adjust as needed
                id='check_reminders', 
                replace_existing=True
            )
            
            # Start the scheduler
            scheduler.start()
            logger.info("Background scheduler started successfully")
            
            # Shut down the scheduler when exiting app
            atexit.register(lambda: shutdown_scheduler())
        else:
            logger.info("Scheduler is already running")
            
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")

def shutdown_scheduler():
    """Safely shut down the scheduler"""
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Background scheduler shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {e}")

# Alternative function to check reminders using current_app (backup method)
def check_reminders_with_current_app():
    """Alternative reminder checker that uses current_app (use if above doesn't work)"""
    try:
        app = current_app._get_current_object()
        
        with app.app_context():
            from focusflow.models import Todo
            
            due_tasks = Todo.query.filter(
                Todo.reminder_active == True,
                Todo.due_date <= datetime.utcnow()
            ).all()
            
            for task in due_tasks:
                logger.info(f"Reminder: Task '{task.content}' is due at {task.due_date}")
                print(f"Reminder: Task '{task.content}' is due at {task.due_date}")
                
    except RuntimeError as context_error:
        logger.error(f"Application context error: {context_error}")
        # Fall back to the create_app method
        check_reminders()
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
