from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = "users"
    __table_args__ = {'mysql_engine': 'InnoDB'}

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    sacco_id = db.Column(db.Integer, db.ForeignKey('saccos.sacco_id'))

    kyc_document = db.Column(db.String(200))
    kyc_verified = db.Column(db.Boolean, default=False)
    otp_code = db.Column(db.String(10))
    otp_expires = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sacco = db.relationship('Sacco', back_populates='members')
    transactions = db.relationship('Transaction', back_populates='user')
    loans = db.relationship('Loan', back_populates='user')
    audit_logs = db.relationship('AuditLog', back_populates='actor')
    notifications = db.relationship('Notification', back_populates='user')
    
    must_change_password = db.Column(db.Boolean, default=True)

    # Password methods
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
