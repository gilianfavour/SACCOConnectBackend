from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.saccoModel import Sacco
from app.models.userModel import User
from app.models.notificationModel import Notification

sacco_bp = Blueprint('sacco_bp', __name__)

# -----------------------------
# Create a new SACCO
# -----------------------------
@sacco_bp.route('/create', methods=['POST'])
@jwt_required()
def create_sacco():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role.lower() not in ['chairperson', 'admin']:
        return jsonify({'error': 'You do not have permission to create a SACCO.'}), 403

    data = request.get_json()
    name = data.get('name')
    bank_account = data.get('bank_account')

    if not name:
        return jsonify({'error': 'SACCO name is required'}), 400

    new_sacco = Sacco(
        name=name,
        bank_account=bank_account,
        created_by=current_user_id
    )

    db.session.add(new_sacco)
    db.session.commit()

    # Auto-assign creator as Chairperson if not already
    if user.role.lower() != 'chairperson':
        user.role = 'Chairperson'
        user.sacco_id = new_sacco.sacco_id
        db.session.commit()

    # Notifications
    if not bank_account:
        notif = Notification(
            user_id=current_user_id,
            subject="Missing ABSA Account",
            message=f'SACCO "{name}" created without ABSSA account. Please add account details.'
        )
        db.session.add(notif)
        db.session.commit()

    # General notification for SACCO creation
    notif_general = Notification(
        user_id=current_user_id,
         subject="SACCO Created",
        message=f'SACCO "{name}" was created successfully.'
    )
    db.session.add(notif_general)
    db.session.commit()

    return jsonify({
        'message': 'SACCO created successfully',
        'sacco': {
            'sacco_id': new_sacco.sacco_id,
            'name': new_sacco.name,
            'bank_account': new_sacco.bank_account,
            'created_by': new_sacco.created_by
        }
    }), 201

# -----------------------------
# Notify SACCO Admin when a new member registers
# -----------------------------
def notify_new_member_registration(new_user: User):
    # Get the SACCO
    sacco = Sacco.query.get(new_user.sacco_id)
    if not sacco:
        return

    # Find Chairperson and Treasurer
    notify_users = User.query.filter(
        (User.sacco_id == sacco.sacco_id) &
        (User.role.in_(['Chairperson', 'Treasurer']))
    ).all()

    for u in notify_users:
        notif = Notification(
            user_id=u.user_id,
            message=f'New member "{new_user.name}" has registered in SACCO "{sacco.name}".'
        )
        db.session.add(notif)
    db.session.commit()


# -----------------------------
# Get all SACCOs
# -----------------------------
@sacco_bp.route('/', methods=['GET'])
@jwt_required()
def get_saccos():
    saccos = Sacco.query.all()
    results = []
    for s in saccos:
        results.append({
            'sacco_id': s.sacco_id,
            'name': s.name,
            'bank_account': s.bank_account,
            'created_by': s.created_by,
            'has_account': bool(s.bank_account)
        })
    return jsonify(results), 200


# -----------------------------
# Get single SACCO
# -----------------------------
@sacco_bp.route('/<int:sacco_id>', methods=['GET'])
@jwt_required()
def get_sacco(sacco_id):
    s = Sacco.query.get_or_404(sacco_id)
    return jsonify({
        'sacco_id': s.sacco_id,
        'name': s.name,
        'bank_account': s.bank_account,
        'created_by': s.created_by,
        'has_account': bool(s.bank_account)
    }), 200


# -----------------------------
# Update SACCO
# -----------------------------
@sacco_bp.route('/<int:sacco_id>', methods=['PUT'])
@jwt_required()
def update_sacco(sacco_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    s = Sacco.query.get_or_404(sacco_id)

    # Granular permission: Admin can edit all, Chairperson only own
    if user.role.lower() == 'chairperson' and s.created_by != current_user_id:
        return jsonify({'error': 'You do not have permission to update this SACCO.'}), 403
    elif user.role.lower() not in ['chairperson', 'admin']:
        return jsonify({'error': 'You do not have permission to update this SACCO.'}), 403

    data = request.get_json()
    name = data.get('name')
    bank_account = data.get('bank_account')

    if name:
        s.name = name
    if bank_account:
        s.bank_account = bank_account

    db.session.commit()

    # Notification for update
    notif = Notification(
        user_id=current_user_id,
        message=f'SACCO "{s.name}" updated successfully.'
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({'message': 'SACCO updated successfully'}), 200


# -----------------------------
# Delete SACCO
# -----------------------------
@sacco_bp.route('/<int:sacco_id>', methods=['DELETE'])
@jwt_required()
def delete_sacco(sacco_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    s = Sacco.query.get_or_404(sacco_id)

    # Granular permission: Admin can delete all, Chairperson only own
    if user.role.lower() == 'chairperson' and s.created_by != current_user_id:
        return jsonify({'error': 'You do not have permission to delete this SACCO.'}), 403
    elif user.role.lower() not in ['chairperson', 'admin']:
        return jsonify({'error': 'You do not have permission to delete this SACCO.'}), 403

    db.session.delete(s)
    db.session.commit()

    # Notification for deletion
    notif = Notification(
        user_id=current_user_id,
        message=f'SACCO "{s.name}" deleted successfully.'
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({'message': 'SACCO deleted successfully'}), 200
