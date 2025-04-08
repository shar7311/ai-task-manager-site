# routes/notification.py
from flask import Blueprint, jsonify, request
from models import Notification
from extensions import db

notification = Blueprint('notification', __name__)

@notification.route('/get_notifications/<int:user_id>', methods=['GET'])
def get_notifications(user_id):
    notifs = Notification.query.filter_by(user_id=user_id, is_read=False).all()
    data = [
        {"id": n.id, "message": n.message, "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S")}
        for n in notifs
    ]
    return jsonify(data)

@notification.route('/mark_as_read/<int:notif_id>', methods=['POST'])
def mark_as_read(notif_id):
    notif = Notification.query.get(notif_id)
    notif.is_read = True
    db.session.commit()
    return jsonify({"message": "Notification marked as read."})
