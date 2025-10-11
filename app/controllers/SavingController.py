from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.savingModel import Saving
from app.models.userModel import User
from app.models.saccoModel import Sacco
from app.models.notificationModel import Notification
from datetime import datetime

saving_bp = Blueprint('saving_bp', __name__)

# -----------------------------
# Create a Saving (Deposit)
# -----------------------------
@saving_bp.route('/deposit', methods=['POST'])
@jwt_required()
def create_saving():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    data = request.get_json()
    amount = data.get('amount')
    sacco_id = data.get('sacco_id')

    if not amount or not sacco_id:
        return jsonify({'error': 'Amount and SACCO ID are required'}), 400

    # Optional: check if SACCO exists
    sacco = Sacco.query.get(sacco_id)
    if not sacco:
        return jsonify({'error': 'SACCO not found'}), 404

    new_saving = Saving(
        user_id=current_user_id,
        sacco_id=sacco_id,
        amount=amount,
        deposited_at=datetime.utcnow()
    )

    db.session.add(new_saving)
    db.session.commit()

    # Notification to user
    notif = Notification(
        user_id=current_user_id,
        message=f'You deposited {amount} into SACCO "{sacco.name}".'
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({
        'message': 'Deposit successful',
        'saving': {
            'saving_id': new_saving.saving_id,
            'amount': new_saving.amount,
            'sacco_id': new_saving.sacco_id,
            'deposited_at': new_saving.deposited_at
        }
    }), 201


# -----------------------------
# Get all savings (privacy aware)
# -----------------------------
@saving_bp.route('/', methods=['GET'])
@jwt_required()
def get_savings():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role.lower() == 'treasurer':
        # Treasurer sees all savings in their SACCO with full details
        savings = Saving.query.filter_by(sacco_id=user.sacco_id).all()
        results = [{
            'saving_id': s.saving_id,
            'user_id': s.user_id,
            'amount': s.amount,
            'sacco_id': s.sacco_id,
            'deposited_at': s.deposited_at
        } for s in savings]

    elif user.role.lower() == 'chairperson':
        # Chairperson sees summary info only
        savings = Saving.query.filter_by(sacco_id=user.sacco_id).all()
        # Aggregate per user
        summary = {}
        for s in savings:
            if s.user_id not in summary:
                summary[s.user_id] = {'total_saved': 0, 'last_deposit': None}
            summary[s.user_id]['total_saved'] += s.amount
            if summary[s.user_id]['last_deposit'] is None or s.deposited_at > summary[s.user_id]['last_deposit']:
                summary[s.user_id]['last_deposit'] = s.deposited_at

        results = []
        for uid, info in summary.items():
            results.append({
                'user_id': uid,
                'total_saved': info['total_saved'],
                'last_deposit': info['last_deposit']
            })

    else:
        # Regular member sees only their own full savings
        savings = Saving.query.filter_by(user_id=current_user_id).all()
        results = [{
            'saving_id': s.saving_id,
            'amount': s.amount,
            'sacco_id': s.sacco_id,
            'deposited_at': s.deposited_at
        } for s in savings]

    return jsonify(results), 200



# -----------------------------
# Get a single saving
# -----------------------------
@saving_bp.route('/<int:saving_id>', methods=['GET'])
@jwt_required()
def get_saving(saving_id):
    saving = Saving.query.get_or_404(saving_id)
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if saving.user_id != current_user_id and user.role.lower() not in ['admin']:
        if user.role.lower() == 'treasurer' and saving.sacco_id == user.sacco_id:
            pass  # Treasurer can view full details
        elif user.role.lower() == 'chairperson' and saving.sacco_id == user.sacco_id:
            # Chairperson sees only summary info
            return jsonify({
                'user_id': saving.user_id,
                'total_saved': saving.amount,  # single deposit, can adjust for aggregation
                'deposited_at': saving.deposited_at
            }), 200
        else:
            return jsonify({'error': 'You do not have permission to view this saving.'}), 403

    return jsonify({
        'saving_id': saving.saving_id,
        'user_id': saving.user_id,
        'amount': saving.amount,
        'sacco_id': saving.sacco_id,
        'deposited_at': saving.deposited_at
    }), 200



# -----------------------------
# Update a saving (optional)
# -----------------------------
@saving_bp.route('/<int:saving_id>', methods=['PUT'])
@jwt_required()
def update_saving(saving_id):
    saving = Saving.query.get_or_404(saving_id)
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    # Only admin can update
    if user.role.lower() != 'admin':
        return jsonify({'error': 'You do not have permission to update this saving.'}), 403

    data = request.get_json()
    amount = data.get('amount')
    if amount:
        saving.amount = amount
        db.session.commit()

    return jsonify({'message': 'Saving updated successfully'}), 200


# -----------------------------
# Delete a saving (optional)
# -----------------------------
@saving_bp.route('/<int:saving_id>', methods=['DELETE'])
@jwt_required()
def delete_saving(saving_id):
    saving = Saving.query.get_or_404(saving_id)
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    # Only admin can delete
    if user.role.lower() != 'admin':
        return jsonify({'error': 'You do not have permission to delete this saving.'}), 403

    db.session.delete(saving)
    db.session.commit()

    return jsonify({'message': 'Saving deleted successfully'}), 200


# -----------------------------
# Savings report (aggregated)
# Chairperson: summary per member
# Treasurer: detailed per member
# -----------------------------
@saving_bp.route('/report', methods=['GET'])
@jwt_required()
def savings_report():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    report_type = request.args.get('type', 'member')  # 'member' or 'daily'

    # Only allow Chairperson, Treasurer, or Admin
    if user.role.lower() not in ['chairperson', 'treasurer', 'admin']:
        return jsonify({'error': 'You do not have permission to view reports.'}), 403

    query = Saving.query
    if user.role.lower() != 'admin':
        query = query.filter_by(sacco_id=user.sacco_id)

    savings = query.all()

    if report_type == 'daily':
        daily_summary = {}
        for s in savings:
            day = s.deposited_at.date()
            if day not in daily_summary:
                daily_summary[day] = 0
            daily_summary[day] += s.amount
        results = [{'date': str(day), 'total_saved': total} for day, total in daily_summary.items()]
    else:  # default member summary
        member_summary = {}
        for s in savings:
            if s.user_id not in member_summary:
                member_summary[s.user_id] = {'total_saved': 0, 'last_deposit': None}
            member_summary[s.user_id]['total_saved'] += s.amount
            if member_summary[s.user_id]['last_deposit'] is None or s.deposited_at > member_summary[s.user_id]['last_deposit']:
                member_summary[s.user_id]['last_deposit'] = s.deposited_at

        results = []
        for uid, info in member_summary.items():
            if user.role.lower() == 'chairperson':
                # Only summary info for Chairperson
                results.append({
                    'user_id': uid,
                    'total_saved': info['total_saved'],
                    'last_deposit': info['last_deposit']
                })
            else:
                # Treasurer/Admin see full details per member
                member_savings = [ 
                    {
                        'saving_id': s.saving_id,
                        'amount': s.amount,
                        'deposited_at': s.deposited_at
                    } for s in savings if s.user_id == uid
                ]
                results.append({
                    'user_id': uid,
                    'total_saved': info['total_saved'],
                    'last_deposit': info['last_deposit'],
                    'savings': member_savings
                })

    return jsonify(results), 200

