from app import db
from datetime import datetime

class Saving(db.Model):
    __tablename__ = 'savings'

    saving_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    sacco_id = db.Column(db.Integer, db.ForeignKey('saccos.sacco_id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    deposited_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='savings')
    sacco = db.relationship('Sacco', backref='savings')

    def __repr__(self):
        return f'<Saving {self.saving_id} - User {self.user_id} - Amount {self.amount}>'
