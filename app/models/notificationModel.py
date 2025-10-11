from datetime import datetime
from app import db

class Notification(db.Model):
    __tablename__ = "notifications"
    
    notification_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    type = db.Column(db.String(50))  # email, sms, system
    message = db.Column(db.String(500))
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', back_populates='notifications')
