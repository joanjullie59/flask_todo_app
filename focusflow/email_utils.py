from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_mail import Message
from flask import render_template, current_app,url_for
from focusflow.extensions import mail


def generate_token(email):
    # Get secret key from current app context
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt="email-confirmation-salt")


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt="email-confirmation-salt", max_age=expiration)
        return email
    except (SignatureExpired, BadSignature):
        return False


def send_verification_email(user_email, token):
    base_url = current_app.config.get('APP_BASE_URL', 'http://localhost:5000')
    confirm_url = f'{base_url}{url_for("main.confirm_email", token=token)}'
    html = render_template('activate.html', confirm_url=confirm_url)
    msg = Message(
        'Please verify your email - FocusFlow',
        recipients=[user_email],
        html=html
    )

    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


# Add this to your config.py or wherever you handle configuration

import os
from datetime import timedelta

class Config:
    # ... your existing config ...
    
    # Email Configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or os.environ.get('MAIL_USERNAME')
    
    # Debug email settings
    MAIL_DEBUG = os.environ.get('MAIL_DEBUG', 'False').lower() == 'true'
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'False').lower() == 'true'

# Create a utility function for sending emails with proper error handling
from flask_mail import Message
from focusflow.extensions import mail
from flask import current_app
import logging

def send_email(to, subject, template, **kwargs):
    """Send email with proper error handling"""
    try:
        # Create message
        msg = Message(
            subject=subject,
            recipients=[to] if isinstance(to, str) else to,
            html=template,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        # Log email attempt
        current_app.logger.info(f"Attempting to send email to {to} with subject: {subject}")
        
        # Send email
        mail.send(msg)
        current_app.logger.info(f"Email sent successfully to {to}")
        return True
        
    except Exception as e:
        # Log the error
        current_app.logger.error(f"Failed to send email to {to}: {str(e)}")
        print(f"Email error: {str(e)}")  # Also print for immediate debugging
        return False

def send_verification_email(user_email, token):
    """Send email verification with error handling"""
    try:
        from flask import url_for
        
        # Generate verification link
        verify_url = url_for('main.verify_email', token=token, _external=True)
        
        # Create HTML email template
        html_body = f"""
        <html>
            <body>
                <h2>Welcome to FocusFlow!</h2>
                <p>Please click the link below to verify your email address:</p>
                <a href="{verify_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a>
                <p>Or copy and paste this link in your browser:</p>
                <p>{verify_url}</p>
                <p>This link will expire in 24 hours.</p>
                <p>If you didn't create an account, please ignore this email.</p>
            </body>
        </html>
        """
        
        # Send the email
        success = send_email(
            to=user_email,
            subject="Verify Your Email - FocusFlow",
            template=html_body
        )
        
        return success
        
    except Exception as e:
        current_app.logger.error(f"Error creating verification email: {str(e)}")
        return False

def test_email_configuration():
    """Test email configuration"""
    try:
        config = current_app.config
        
        print("=== EMAIL CONFIGURATION DEBUG ===")
        print(f"MAIL_SERVER: {config.get('MAIL_SERVER')}")
        print(f"MAIL_PORT: {config.get('MAIL_PORT')}")
        print(f"MAIL_USE_TLS: {config.get('MAIL_USE_TLS')}")
        print(f"MAIL_USE_SSL: {config.get('MAIL_USE_SSL')}")
        print(f"MAIL_USERNAME: {config.get('MAIL_USERNAME')}")
        print(f"MAIL_PASSWORD: {'*' * len(str(config.get('MAIL_PASSWORD', '')))}")
        print(f"MAIL_DEFAULT_SENDER: {config.get('MAIL_DEFAULT_SENDER')}")
        print("================================")
        
        # Try to send a test email
        if config.get('MAIL_USERNAME'):
            success = send_email(
                to=config.get('MAIL_USERNAME'),  # Send to yourself as test
                subject="FocusFlow Email Test",
                template="<p>If you receive this, your email configuration is working!</p>"
            )
            return success
        else:
            print("No MAIL_USERNAME configured")
            return False
            
    except Exception as e:
        print(f"Email configuration test failed: {e}")
        return False
