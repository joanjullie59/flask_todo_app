from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from focusflow.extensions import db
from datetime import datetime
from sqlalchemy import Boolean

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    tasks = db.relationship('Todo', backref='owner', lazy=True)
    email_verified = db.Column(Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    #for better debugging and developer friendly printouts
    def __repr__(self):
        return f'<User {self.email!r}>'


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    category_id =db.Column(db.Integer,db.ForeignKey('category.id'),nullable=True)
    #for handling due dates
    due_date=db.Column(db.DateTime, nullable=True)
    reminder_active = db.Column(db.Boolean, default=False)
    reminder_time = db.Column(db.Integer, default=30)  # store reminder lead time in minutes

    @property
    def is_reminder_due(self):
        return self.due_date and self.reminder_active and (self.due_date <= datetime.utcnow())

    def __repr__(self):
        return f'<Task id={self.id} content={self.content!r}>'


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    tasks = db.relationship('Todo', backref='category', lazy=True,foreign_keys='Todo.category_id')

