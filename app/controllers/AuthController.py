from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import random
from app import db
from app.models.userModel import User
from app.models.saccoModel import Sacco

auth_bp = Blueprint('auth_bp', __name__)

# -----------------------------
# Invite User (Chairperson/Treasurer only)
# -----------------------------
@auth_bp.route('/invite', methods=['POST'])
@jwt_required()
def invite_user():
    data = request.get_json()
    email = data.get('email')
    role = data.get('role')
    sacco_id = data.get('sacco_id')

    current_user = User.query.get(get_jwt_identity())

    # Validate SACCO exists
    sacco = Sacco.query.get(sacco_id)
    if not sacco:
        return jsonify({'error': 'SACCO does not exist.'}), 404

    # Ensure inviter belongs to the SACCO
    if current_user.sacco_id != sacco_id:
        return jsonify({'error': 'You can only invite users to your own SACCO.'}), 403

    # Role-based enforcement
    if role.lower() == 'treasurer' and current_user.role.lower() != 'chairperson':
        return jsonify({'error': 'Only Chairperson can invite Treasurer.'}), 403
    if role.lower() == 'member' and current_user.role.lower() != 'treasurer':
        return jsonify({'error': 'Only Treasurer can invite Members.'}), 403

     # Check that inviter belongs to this SACCO
    if current_user.sacco_id != sacco_id:
        return jsonify({'error': 'You do not belong to this SACCO.'}), 403

    # Check for existing user or pending invite
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        if existing_user.kyc_verified:
            return jsonify({'error': 'User already registered.'}), 400
        else:
            return jsonify({'error': 'User already invited and pending registration.'}), 400

    # Generate OTP for registration
    otp_code = str(random.randint(100000, 999999))
    otp_expires = datetime.utcnow() + timedelta(hours=2)

    new_user = User(
        email=email,
        role=role,
        sacco_id=sacco_id,
        otp_code=otp_code,
        otp_expires=otp_expires,
        must_change_password=True  # Force password change after first login
    )

    db.session.add(new_user)
    db.session.commit()

    # TODO: Send OTP via email
    # send_email(email, otp_code)

    return jsonify({'message': f'Invitation sent to {email}.', 'otp_code': otp_code}), 201

# -----------------------------
# Public Signup (no OTP required)
# -----------------------------
@auth_bp.route('/signup', methods=['POST'])
def signup_user():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')

    if not all([name, email, phone, password]):
        return jsonify({'error': 'All fields are required.'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered.'}), 400

    # Create new user as Chairperson by default
    new_user = User(
        name=name,
        email=email,
        phone=phone,
        role='Chairperson',
        kyc_verified=True  # no OTP needed
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        'message': 'Signup successful. You can now login.',
        'user': {
            'user_id': new_user.user_id,
            'name': new_user.name,
            'email': new_user.email,
            'role': new_user.role
        }
    }), 201


# -----------------------------
# Register User via OTP
# -----------------------------
@auth_bp.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    otp_code = data.get('otp_code')
    name = data.get('name')
    phone = data.get('phone')

    if not all([email, password, otp_code, name, phone]):
        return jsonify({'error': 'All fields are required.'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not invited yet.'}), 404

    if user.otp_code != otp_code:
        return jsonify({'error': 'Invalid OTP.'}), 400

    if datetime.utcnow() > user.otp_expires:
        return jsonify({'error': 'OTP expired.'}), 400

    # Set user details and password
    user.name = name
    user.phone = phone
    user.set_password(password)
    user.kyc_verified = True
    user.otp_code = None
    user.otp_expires = None

    db.session.commit()

    return jsonify({'message': 'Registration complete. Please login.'}), 200


# -----------------------------
# Login
# -----------------------------
@auth_bp.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    email_or_phone = data.get('email_or_phone')
    password = data.get('password')

    if not email_or_phone or not password:
        return jsonify({'error': 'Email/Phone and password are required'}), 400

    user = User.query.filter(
        (User.email == email_or_phone) | (User.phone == email_or_phone)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    # Ensure user has a valid SACCO
    # sacco = Sacco.query.get(user.sacco_id)
    # if not sacco:
    #     return jsonify({'error': 'User not assigned to a valid SACCO.'}), 403

    if not user.kyc_verified:
        return jsonify({'error': 'KYC not verified. Complete registration first.'}), 403

    access_token = create_access_token(identity=user.user_id, expires_delta=timedelta(hours=8))

    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'must_change_password': user.must_change_password,
        'user': {
            'user_id': user.user_id,
            'name': user.name,
            'role': user.role,
            'sacco_id': user.sacco_id
        }
    }), 200


# -----------------------------
# OTP Verification (optional, can remove if /register handles it)
# -----------------------------
@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp_code = data.get('otp_code')

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.otp_code != otp_code:
        return jsonify({'error': 'Invalid OTP'}), 400

    if datetime.utcnow() > user.otp_expires:
        return jsonify({'error': 'OTP expired'}), 400

    user.kyc_verified = True
    user.otp_code = None
    user.otp_expires = None

    db.session.commit()

    return jsonify({'message': 'OTP verified successfully. Account activated.'}), 200


# -----------------------------
# Force Password Change
# -----------------------------
@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')

    user = User.query.get(get_jwt_identity())

    if not old_password or not new_password:
        return jsonify({'error': 'Both old and new password are required.'}), 400

    if not user.check_password(old_password):
        return jsonify({'error': 'Old password is incorrect.'}), 400

    user.set_password(new_password)
    user.must_change_password = False
    db.session.commit()

    return jsonify({'message': 'Password changed successfully.'}), 200
