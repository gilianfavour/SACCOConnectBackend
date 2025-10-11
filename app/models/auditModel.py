from datetime import datetime
from app import db

class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    action = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='general') # money, registration, loan
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    actor = db.relationship('User', back_populates='audit_logs')
