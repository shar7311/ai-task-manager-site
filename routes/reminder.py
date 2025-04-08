# routes/reminder.py
from flask import Blueprint, request, jsonify
from models import Reminder
from extensions import db
from datetime import datetime

reminder = Blueprint('reminder', __name__)

@reminder.route('/add_reminder', methods=['POST'])
def add_reminder():
    data = request.get_json()
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    new_reminder = Reminder(
        user_id=data['user_id'],
        message=data['message'],
        remind_at=datetime.strptime(data['remind_at'], "%Y-%m-%d %H:%M:%S")
    )
    db.session.add(new_reminder)
    db.session.commit()
    return jsonify({"status": "success", "message": "Reminder added."}), 200
