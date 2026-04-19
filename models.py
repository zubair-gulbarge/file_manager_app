from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'admin' or 'user'
    
    # Relationship to link files to users
    files = db.relationship('File', backref='owner', lazy=True)

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    
    # Feature 1: Store file size in bytes
    size = db.Column(db.Integer, default=0)
    
    # Feature 2: Store file category
    category = db.Column(db.String(50), default='General')
    
    # Modern timezone-aware datetime
    upload_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Foreign Key linking back to User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)