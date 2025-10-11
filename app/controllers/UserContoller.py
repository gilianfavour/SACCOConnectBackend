from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import random
from app import db
from app.models.userModel import User
from app.models.saccoModel import Sacco
from app.models.notificationModel import Notification

user_bp = Blueprint('user_bp', __name__)

# -----------------------------
# Invite User (Chairperson/Treasurer only)
# -----------------------------
@user_bp.route('/invite', methods=['POST'])
@jwt_required()
def invite_user():
    data = request.get_json()
    email = data.get('email')
    role = data.get('role')
    sacco_id = data.get('sacco_id')

    current_user = User.query.get(get_jwt_identity())

    # Role-based enforcement
    if role.lower() == 'treasurer' and current_user.role.lower() != 'chairperson':
        return jsonify({'error': 'Only Chairperson can invite Treasurer.'}), 403
    if role.lower() == 'member' and current_user.role.lower() != 'treasurer':
        return jsonify({'error': 'Only Treasurer can invite Members.'}), 403

    # Check for existing user
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'User with this email already exists.'}), 400

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

    # Notification
    notif = Notification(
        user_id=current_user.user_id,
        message=f'Invitation sent to {email} as {role}.'
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({'message': f'Invitation sent to {email}.', 'otp_code': otp_code}), 201


# -----------------------------
# Register User via OTP
# -----------------------------
@user_bp.route('/register', methods=['POST'])
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
# Get all users (filtered by SACCO)
# -----------------------------
@user_bp.route('/', methods=['GET'])
@jwt_required()
def get_users():
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)

    if current_user.role.lower() not in ['admin', 'chairperson', 'treasurer']:
        return jsonify({'error': 'Access denied.'}), 403

    users = User.query.all() if current_user.role.lower() == 'admin' else User.query.filter_by(sacco_id=current_user.sacco_id).all()

    result = [{
        'user_id': u.user_id,
        'name': u.name,
        'email': u.email,
        'phone': u.phone,
        'role': u.role,
        'sacco_id': u.sacco_id,
        'kyc_verified': u.kyc_verified,
        'must_change_password': u.must_change_password
    } for u in users]

    return jsonify(result), 200


# -----------------------------
# Get single user
# -----------------------------
@user_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    user = User.query.get_or_404(user_id)

    if current_user.role.lower() not in ['admin', 'chairperson', 'treasurer'] and current_user.user_id != user.user_id:
        return jsonify({'error': 'Access denied.'}), 403

    return jsonify({
        'user_id': user.user_id,
        'name': user.name,
        'email': user.email,
        'phone': user.phone,
        'role': user.role,
        'sacco_id': user.sacco_id,
        'kyc_verified': user.kyc_verified,
        'must_change_password': user.must_change_password
    }), 200


# -----------------------------
# Update user (name, phone, role)
# -----------------------------
@user_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    user = User.query.get_or_404(user_id)

    data = request.get_json()
    name = data.get('name')
    phone = data.get('phone')
    role = data.get('role')

    # Permissions check
    if current_user.role.lower() == 'chairperson' and user.sacco_id != current_user.sacco_id:
        return jsonify({'error': 'Cannot edit users outside your SACCO.'}), 403
    elif current_user.role.lower() == 'treasurer':
        if user.role.lower() in ['chairperson', 'treasurer'] or user.sacco_id != current_user.sacco_id:
            return jsonify({'error': 'Access denied.'}), 403
    elif current_user.role.lower() not in ['admin', 'chairperson', 'treasurer']:
        return jsonify({'error': 'Access denied.'}), 403

    if name:
        user.name = name
    if phone:
        user.phone = phone
    if role:
        user.role = role

    db.session.commit()

    # Notification
    notif = Notification(
        user_id=current_user.user_id,
        message=f'User "{user.name}" updated successfully.'
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({'message': 'User updated successfully.'}), 200


# -----------------------------
# Delete user
# -----------------------------
@user_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    user = User.query.get_or_404(user_id)

    # Permissions check
    if current_user.role.lower() == 'chairperson' and user.sacco_id != current_user.sacco_id:
        return jsonify({'error': 'Cannot delete users outside your SACCO.'}), 403
    elif current_user.role.lower() == 'treasurer':
        if user.role.lower() in ['chairperson', 'treasurer'] or user.sacco_id != current_user.sacco_id:
            return jsonify({'error': 'Access denied.'}), 403
    elif current_user.role.lower() not in ['admin', 'chairperson', 'treasurer']:
        return jsonify({'error': 'Access denied.'}), 403

    db.session.delete(user)
    db.session.commit()

    # Notification
    notif = Notification(
        user_id=current_user.user_id,
        message=f'User "{user.name}" deleted successfully.'
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({'message': 'User deleted successfully.'}), 200
