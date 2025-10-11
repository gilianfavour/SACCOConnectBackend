from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models.loanModal import Loan
from app.models.userModel import User
from app.models.notificationModel import Notification

loan_bp = Blueprint('loan_bp', __name__)

# -----------------------------
# Create Loan Request (Members)
# -----------------------------
@loan_bp.route('/create', methods=['POST'])
@jwt_required()
def create_loan():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role.lower() != 'member':
        return jsonify({'error': 'Only members can request loans.'}), 403

    data = request.get_json()
    amount = data.get('amount')
    reason = data.get('reason')

    if not amount or not reason:
        return jsonify({'error': 'Amount and reason are required.'}), 400

    new_loan = Loan(
        user_id=current_user_id,
        sacco_id=user.sacco_id,
        amount=amount,
        reason=reason,
        status='Pending',
        requested_at=datetime.utcnow()
    )

    db.session.add(new_loan)
    db.session.commit()

    # Notification for Treasurer/Chairperson
    notif = Notification(
        user_id=None,  # Can be assigned to all admins/treasurers in SACCO
        message=f'New loan request from {user.name} for amount {amount}.'
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({'message': 'Loan request submitted successfully.', 'loan_id': new_loan.loan_id}), 201


# -----------------------------
# Approve/Reject Loan (Treasurer/Chairperson)
# -----------------------------
@loan_bp.route('/<int:loan_id>/decision', methods=['POST'])
@jwt_required()
def decide_loan(loan_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role.lower() not in ['treasurer', 'chairperson', 'admin']:
        return jsonify({'error': 'You do not have permission to approve/reject loans.'}), 403

    loan = Loan.query.get_or_404(loan_id)
    data = request.get_json()
    decision = data.get('decision')  # 'Approved' or 'Rejected'
    comment = data.get('comment', '')

    if decision not in ['Approved', 'Rejected']:
        return jsonify({'error': 'Decision must be Approved or Rejected.'}), 400

    loan.status = decision
    loan.decision_by = current_user_id
    loan.decision_at = datetime.utcnow()
    loan.comment = comment

    db.session.commit()

    # Notification to member
    notif = Notification(
        user_id=loan.user_id,
        message=f'Your loan request for {loan.amount} has been {decision.lower()}.'
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({'message': f'Loan {decision.lower()} successfully.'}), 200


# -----------------------------
# Get all loans (Admin/Treasurer/Chairperson)
# -----------------------------
@loan_bp.route('/', methods=['GET'])
@jwt_required()
def get_loans():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role.lower() == 'admin':
        loans = Loan.query.all()
    else:
        loans = Loan.query.filter_by(sacco_id=user.sacco_id).all()

    result = []
    for loan in loans:
        result.append({
            'loan_id': loan.loan_id,
            'user_id': loan.user_id,
            'sacco_id': loan.sacco_id,
            'amount': loan.amount,
            'reason': loan.reason,
            'status': loan.status,
            'requested_at': loan.requested_at,
            'decision_by': loan.decision_by,
            'decision_at': loan.decision_at,
            'comment': loan.comment
        })
    return jsonify(result), 200


# -----------------------------
# Get single loan details
# -----------------------------
@loan_bp.route('/<int:loan_id>', methods=['GET'])
@jwt_required()
def get_loan(loan_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    loan = Loan.query.get_or_404(loan_id)

    # Members can only view their own loans
    if user.role.lower() == 'member' and loan.user_id != current_user_id:
        return jsonify({'error': 'Access denied.'}), 403

    # Others see only SACCO loans
    if user.role.lower() in ['treasurer', 'chairperson'] and loan.sacco_id != user.sacco_id:
        return jsonify({'error': 'Access denied.'}), 403

    return jsonify({
        'loan_id': loan.loan_id,
        'user_id': loan.user_id,
        'sacco_id': loan.sacco_id,
        'amount': loan.amount,
        'reason': loan.reason,
        'status': loan.status,
        'requested_at': loan.requested_at,
        'decision_by': loan.decision_by,
        'decision_at': loan.decision_at,
        'comment': loan.comment
    }), 200


# -----------------------------
# Delete Loan (Admin only)
# -----------------------------
@loan_bp.route('/<int:loan_id>', methods=['DELETE'])
@jwt_required()
def delete_loan(loan_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role.lower() != 'admin':
        return jsonify({'error': 'Only admin can delete loans.'}), 403

    loan = Loan.query.get_or_404(loan_id)
    db.session.delete(loan)
    db.session.commit()

    # Notification
    notif = Notification(
        user_id=loan.user_id,
        message=f'Your loan request for {loan.amount} has been deleted by admin.'
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({'message': 'Loan deleted successfully.'}), 200
