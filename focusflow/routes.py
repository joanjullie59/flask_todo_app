from firebase_admin.auth import UserNotFoundError, EmailAlreadyExistsError
from flask import Blueprint, render_template, redirect, url_for, flash, abort,current_app
from flask_login import login_user, login_required, logout_user, current_user, UserMixin
from focusflow.models import User, Todo, Category
from focusflow.forms import TaskForm, RegistrationForm
from focusflow.extensions import db
from focusflow.forms import LoginForm, ResendVerificationForm
import os
from flask import request, jsonify, g
from focusflow.email_utils import generate_token, send_verification_email, confirm_token
from firebase_admin import auth as firebase_auth

main = Blueprint('main', __name__)

# Initialize Firebase Admin SDK (do this once, e.g. in extensions or app factory)
current_dir = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(current_dir, '..', 'focusflow-97803-firebase-adminsdk-fbsvc-3e4b6274ee.json')


# User class wrapper for Flask-Login to track session user from Firebase
class FirebaseUser(UserMixin):
    def __init__(self, uid, email, email_verified):
        self.id = uid
        self.email = email
        self.email_verified = email_verified


def verify_firebase_token():
    id_token = request.headers.get('Authorization')
    if not id_token:
        return None

    id_token = id_token.split(' ').pop()  # Remove 'Bearer ' if present
    try:
        decoded_token = firebase_auth.verify_id_token(id_token)
        # Attach user info to request context
        g.current_user = decoded_token
        return decoded_token
    except Exception:
        return None


@main.route("/protected")
def protected():
    user = verify_firebase_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"message": f"Hello {user['email']}!"})


# Helper to load Firebase user for Flask-Login
def load_firebase_user(uid):
    try:
        user_record = firebase_auth.get_user(uid)
        return FirebaseUser(user_record.uid, user_record.email, user_record.email_verified)
    except UserNotFoundError:
        return None


# Register route - creates Firebase user and sends email verification
@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            email = form.email.data.strip().lower()
            password = form.password.data
            
            current_app.logger.info(f"Registration attempt for email: {email}")
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                if existing_user.email_verified:
                    flash('This email is already registered and verified. Please login.', 'info')
                    return redirect(url_for('main.login'))
                else:
                    flash('This email is registered but not verified. Please check your email or request a new verification.', 'warning')
                    return render_template('register.html', form=form)
            
            # Create new user
            hashed_password = generate_password_hash(password)
            user = User(
                email=email,
                password_hash=hashed_password,
                email_verified=False
            )
            
            # Save user to database
            db.session.add(user)
            db.session.commit()
            
            current_app.logger.info(f"New user registered: {email}")
            
            # Send verification email
            try:
                # Import here to avoid circular imports
                from focusflow.email_utils import send_verification_email
                
                success, message = send_verification_email(email)
                
                if success:
                    flash('Registration successful! Please check your email to verify your account. Check your spam folder if you don\'t see it.', 'success')
                    current_app.logger.info(f"Verification email sent successfully to {email}")
                else:
                    flash(f'Account created but failed to send verification email: {message}. Please use the "Resend Verification" option.', 'warning')
                    current_app.logger.error(f"Failed to send verification email to {email}: {message}")
                    
            except Exception as email_error:
                error_msg = str(email_error)
                flash(f'Account created but email verification failed: {error_msg}. Please use the "Resend Verification" option.', 'warning')
                current_app.logger.error(f"Email verification error for {email}: {error_msg}")
            
            return redirect(url_for('main.login'))
            
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            current_app.logger.error(f"Registration error for {email}: {error_msg}")
            flash(f'Registration failed: {error_msg}. Please try again.', 'error')
            return render_template('register.html', form=form)
    
    return render_template('register.html', form=form)



# Login route - verifies user via Firebase and only logs in if email verified
@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    
    if form.validate_on_submit():
        try:
            email = form.email.data.strip().lower()
            password = form.password.data
            
            current_app.logger.info(f"Login attempt for email: {email}")
            
            # Find user
            user = User.query.filter_by(email=email).first()
            
            if not user:
                current_app.logger.warning(f"Login failed - user not found: {email}")
                flash('Invalid email or password.', 'error')
                return render_template('login.html', form=form)
            
            if not check_password_hash(user.password_hash, password):
                current_app.logger.warning(f"Login failed - incorrect password: {email}")
                flash('Invalid email or password.', 'error')
                return render_template('login.html', form=form)
            
            # Check if email is verified
            if not user.email_verified:
                current_app.logger.info(f"Login blocked - email not verified: {email}")
                flash('Please verify your email before logging in. Check your inbox or request a new verification email.', 'warning')
                return render_template('login.html', form=form)
            
            # Login user
            login_user(user, remember=form.remember_me.data)
            current_app.logger.info(f"User logged in successfully: {email}")
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            current_app.logger.error(f"Login error for {email}: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
            return render_template('login.html', form=form)
    
    # For GET request or failed validation
    return render_template('login.html', form=form)



# Protect your index route as before with login_required
@main.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = TaskForm()

    if form.validate_on_submit():
        category_id = form.category.data
        task_content = form.content.data.strip()

        if not task_content:
            flash('Task content cannot be empty.', 'warning')
            return redirect(url_for('main.index'))

        # Handle category selection
        category = None
        if category_id and category_id != 0:  # 0 is the "Select a category..." option
            category = Category.query.get(category_id)

        new_task = Todo(
            content=task_content,
            category=category,
            user_id=current_user.id,
            due_date=form.due_date.data,
            reminder_active=form.reminder_active.data,
            reminder_time=int(form.reminder_time.data)
        )

        try:
            db.session.add(new_task)
            db.session.commit()
            flash('Task added successfully!', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            flash(f'Error adding task: {e}', 'danger')
            return redirect(url_for('main.index'))

    tasks = Todo.query.filter_by(user_id=current_user.id).order_by(Todo.date_created).all()
    return render_template('index.html', form=form, tasks=tasks)


@main.route('/update/<int:task_id>', methods=['GET', 'POST'])
@login_required
def update(task_id):
    task = Todo.query.get_or_404(task_id)

    # ownership check
    if task.user_id != current_user.id:
        abort(403)

    form = TaskForm(obj=task)

    # Set the current category as selected
    if task.category:
        form.category.data = task.category.id

    if form.validate_on_submit():
        category_id = form.category.data
        task.content = form.content.data.strip()

        # Handle category selection
        if category_id and category_id != 0:
            task.category = Category.query.get(category_id)
        else:
            task.category = None

        task.due_date = form.due_date.data

        try:
            db.session.commit()
            flash('Task updated successfully!', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            flash(f'There was an issue updating your task: {str(e)}', 'danger')
            return redirect(url_for('main.update', task_id=task_id))
    else:
        return render_template('update.html', form=form, task=task)


# Logout route
@main.route('/logout')
@login_required
def logout():
    current_app.logger.info(f"User logged out: {current_user.email}")
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.login'))


# we create a new route
# we need a unique identifier like primary key
@main.route('/delete/<int:task_id>')
@login_required
def delete(task_id):
    task_to_delete = Todo.query.get_or_404(task_id)

    # check for ownership....does the current user own the task?
    if task_to_delete.user_id != current_user.id:
        abort(403)  # forbidden error, user not allowed to do this
    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        flash('Task deleted successfully.', 'success')  # <- flash message
    except Exception as e:
        flash(f'There was a problem deleting that task: {str(e)}', 'danger')
    return redirect(url_for('main.index'))



# allows users to request a new verification email
@main.route('/resend_verification', methods=['GET', 'POST'])
def resend_verification():
    form = ResendVerificationForm()
    
    if form.validate_on_submit():
        try:
            email = form.email.data.strip().lower()
            
            current_app.logger.info(f"Resend verification attempt for: {email}")
            
            # Find user
            user = User.query.filter_by(email=email).first()
            
            if not user:
                # Don't reveal if email exists for security
                flash('If an account with this email exists and is not verified, a verification email has been sent.', 'info')
                return render_template('resend_verification.html', form=form)
            
            if user.email_verified:
                flash('This email is already verified. You can login normally.', 'info')
                return redirect(url_for('main.login'))
            
            # Send verification email
            try:
                from focusflow.email_utils import send_verification_email
                
                success, message = send_verification_email(email)
                
                if success:
                    flash('Verification email sent successfully! Please check your inbox and spam folder.', 'success')
                    current_app.logger.info(f"Verification email resent to {email}")
                else:
                    flash(f'Failed to send verification email: {message}. Please contact support.', 'error')
                    current_app.logger.error(f"Failed to resend verification email to {email}: {message}")
                    
            except Exception as email_error:
                error_msg = str(email_error)
                flash(f'Failed to send verification email: {error_msg}. Please contact support.', 'error')
                current_app.logger.error(f"Error resending verification email to {email}: {error_msg}")
            
            return render_template('resend_verification.html', form=form)
            
        except Exception as e:
            current_app.logger.error(f"Resend verification error: {str(e)}")
            flash('An error occurred. Please try again.', 'error')
            return render_template('resend_verification.html', form=form)
    
    return render_template('resend_verification.html', form=form)



@main.route('/verify_email/<token>')
def verify_email(token):
    try:
        current_app.logger.info(f"Email verification attempt with token: {token[:20]}...")
        
        # Import here to avoid circular imports
        from focusflow.email_utils import verify_email_token
        
        # Verify the token
        email = verify_email_token(token)
        
        if not email:
            current_app.logger.warning(f"Invalid or expired verification token: {token[:20]}...")
            flash('The verification link is invalid or has expired. Please request a new one.', 'error')
            return redirect(url_for('main.resend_verification'))
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user:
            current_app.logger.error(f"User not found for verified email: {email}")
            flash('User not found. Please register again.', 'error')
            return redirect(url_for('main.register'))
        
        if user.email_verified:
            current_app.logger.info(f"Email already verified for: {email}")
            flash('Your email is already verified. You can login normally.', 'info')
            return redirect(url_for('main.login'))
        
        # Verify the user
        user.email_verified = True
        db.session.commit()
        
        current_app.logger.info(f"Email verified successfully for {email}")
        flash('Email verified successfully! You can now login.', 'success')
        return redirect(url_for('main.login'))
        
    except Exception as e:
        current_app.logger.error(f"Email verification error: {str(e)}")
        flash('An error occurred during verification. Please try again.', 'error')
        return redirect(url_for('main.resend_verification'))


@main.route('/debug-categories')
@login_required
def debug_categories():
    # Check what categories exist
    categories = Category.query.all()
    category_list = [f"{c.id}: {c.name}" for c in categories]

    # Check form category choices
    form = TaskForm()
    form_choices = form.category.choices if hasattr(form.category, 'choices') else "No choices attribute"

    return f"""
    <h3>Category Debug</h3>
    <p><strong>Categories in database:</strong> {category_list}</p>
    <p><strong>Form category choices:</strong> {form_choices}</p>
    <p><strong>Form category type:</strong> {type(form.category)}</p>
    """
@main.route('/test-simple')
def test_simple():
    # Simple test without forms
    categories = Category.query.all()
    if categories:
        return f"Categories found: {[c.name for c in categories]}"
    else:
        return "No categories found in database!"


@main.route('/test_email')
def test_email_route():
    """Test email configuration - REMOVE IN PRODUCTION"""
    try:
        success, message = test_email_config()
        
        if success:
            return f"✅ Email test successful: {message}"
        else:
            return f"❌ Email test failed: {message}"
            
    except Exception as e:
        return f"❌ Email test error: {str(e)}"





