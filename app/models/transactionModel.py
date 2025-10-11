from datetime import datetime
from app import db

class Transaction(db.Model):
    __tablename__ = "transactions"
    
    transaction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    sacco_id = db.Column(db.Integer, db.ForeignKey('saccos.sacco_id'))
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # deposit, withdrawal
    source = db.Column(db.String(50), default='manual') # mobile_money, bank, manual
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='transactions')
    sacco = db.relationship('Sacco', back_populates='transactions')
