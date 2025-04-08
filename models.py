from extensions import db
from datetime import datetime
reminded = db.Column(db.Boolean, default=False)


class Email(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(500))
    snippet = db.Column(db.Text)
    date_received = db.Column(db.DateTime, default=datetime.utcnow)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CalendarEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class DailyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<DailyLog {self.date}>'

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    deadline = db.Column(db.DateTime)
    estimated_time = db.Column(db.Float)
    importance_level = db.Column(db.Integer)
    category = db.Column(db.String(100))
    priority = db.Column(db.String(20))
    status = db.Column(db.String(20), default="pending")
    reminded = db.Column(db.Boolean, default=False)  # 👈 Make sure this is added
    # models.py

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    remind_at = db.Column(db.DateTime, nullable=False)
    is_sent = db.Column(db.Boolean, default=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

class User(db.Model):
    __tablename__ = 'user'  # This must match the foreign key string

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    reminders = db.relationship('Reminder', backref='user', lazy=True)



    def __repr__(self):
        return f'<Task {self.title}>'
