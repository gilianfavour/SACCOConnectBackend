from datetime import datetime
from app import db

class Sacco(db.Model):
    __tablename__ = "saccos"
    __table_args__ = {'mysql_engine': 'InnoDB'}

    sacco_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    
    # Not a foreign key for now — just stores the user_id
    created_by = db.Column(db.Integer, nullable=True)

    bank_account = db.Column(db.String(50))
    total_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship('User', back_populates='sacco')
    transactions = db.relationship('Transaction', back_populates='sacco')
    loans = db.relationship('Loan', back_populates='sacco')
