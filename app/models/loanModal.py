from datetime import datetime
from app import db

class Loan(db.Model):
    __tablename__ = "loans"
    
    loan_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    sacco_id = db.Column(db.Integer, db.ForeignKey('saccos.sacco_id'))
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, repaid
    repayment_due = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='loans')
    sacco = db.relationship('Sacco', back_populates='loans')
