from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(500))
    snippet = db.Column(db.Text)
    date_received = db.Column(db.DateTime, default=datetime.utcnow)  # Stores when the email was received


class Contact(db.Model):
    id = db.Column(db.String(255), primary_key=True)  # Google Contact ID
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)  # Not all contacts have emails
    phone = db.Column(db.String(20), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Track when stored


class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

