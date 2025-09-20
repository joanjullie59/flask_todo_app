from wtforms import StringField, SubmitField, BooleanField, SelectField, PasswordField,TextAreaField
from focusflow.models import Category
from wtforms.fields.datetime import DateTimeLocalField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


# REMOVE the category_query function - we don't need it anymore
# REMOVE the QuerySelectField import - we're not using it

class TaskForm(FlaskForm):
    content = StringField('Task Content', validators=[DataRequired()])

    # Use regular SelectField with empty choices - we'll populate them in __init__
    category = SelectField('Category', choices=[], coerce=int)

    due_date = DateTimeLocalField('Due Date', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    reminder_active = BooleanField('Set Reminder')
    reminder_time = SelectField('Remind me', choices=[
        ('10', '10 minutes before'),
        ('30', '30 minutes before'),
        ('60', '1 hour before'),
        ('120', '2 hours before')
    ], default='30')
    submit = SubmitField('Add Task')

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        # Populate categories from database when form is created
        categories = Category.query.order_by(Category.name).all()
        self.category.choices = [(0, 'Select a category...')] + [(c.id, c.name) for c in categories]


class RegistrationForm(FlaskForm):
       username = StringField('Username', validators=[
        DataRequired(message="Username is required"),
        Length(min=3, max=20, message="Username must be between 3 and 20 characters")
    ])
    
    email = StringField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Please enter a valid email address")
    ])
    
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=6, message="Password must be at least 6 characters long")
    ])
    
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords must match")
    ])
    
    submit = SubmitField('Register')



class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')


class ResendVerificationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Resend Verification')


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

  # Custom validation for username
    def validate_username(self, username):
        # Check if username contains only alphanumeric characters and underscores
        if not re.match("^[a-zA-Z0-9_]+$", username.data):
            raise ValidationError("Username can only contain letters, numbers, and underscores")
        
        # Check if username already exists
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("Username already exists. Please choose a different one.")
    
    # Custom validation for email
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("Email already registered. Please use a different email.")
    
    # Custom validation for password strength
    def validate_password(self, password):
        password_value = password.data
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password_value):
            raise ValidationError("Password must contain at least one uppercase letter")
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password_value):
            raise ValidationError("Password must contain at least one lowercase letter")
        
        # Check for at least one digit
        if not re.search(r'[0-9]', password_value):
            raise ValidationError("Password must contain at least one number")

