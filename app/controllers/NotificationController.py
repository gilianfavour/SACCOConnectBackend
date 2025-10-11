from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.notificationModel import Notification
from app.models.userModel import User
from datetime import datetime

notification_bp = Blueprint('notification_bp', __name__)

# -----------------------------
# Get all notifications for the logged-in user
# -----------------------------
@notification_bp.route('/all', methods=['GET'])
@jwt_required()
def get_notifications():
    current_user_id = get_jwt_identity()
    notifications = Notification.query.filter_by(user_id=current_user_id).order_by(Notification.created_at.desc()).all()
    
    results = []
    for n in notifications:
        results.append({
            'notification_id': n.notification_id,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': n.created_at
        })

    return jsonify({'notifications': results}), 200


# -----------------------------
# Mark a single notification as read
# -----------------------------
@notification_bp.route('/read/<int:notification_id>', methods=['POST'])
@jwt_required()
def mark_notification_read(notification_id):
    current_user_id = get_jwt_identity()
    notification = Notification.query.get_or_404(notification_id)

    if notification.user_id != current_user_id:
        return jsonify({'error': 'You do not have permission to mark this notification.'}), 403

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'message': 'Notification marked as read.'}), 200


# -----------------------------
# Mark all notifications as read
# -----------------------------
@notification_bp.route('/read-all', methods=['POST'])
@jwt_required()
def mark_all_notifications_read():
    current_user_id = get_jwt_identity()
    notifications = Notification.query.filter_by(user_id=current_user_id, is_read=False).all()

    for n in notifications:
        n.is_read = True
        n.read_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'message': f'{len(notifications)} notifications marked as read.'}), 200
