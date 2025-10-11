from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app import db
from app.models.transactionModel import Transaction
from app.models.userModel import User
from app.models.savingModel import Saving
from app.models.loanModal import Loan
from app.models.notificationModel import Notification

transaction_bp = Blueprint('transaction_bp', __name__)

# -----------------------------
# Create a new transaction (deposit, withdrawal, loan repayment)
# -----------------------------
@transaction_bp.route('/create', methods=['POST'])
@jwt_required()
def create_transaction():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    data = request.get_json()
    user_id = data.get('user_id')
    trans_type = data.get('type')  # deposit, withdrawal, loan_payment
    amount = data.get('amount')
    loan_id = data.get('loan_id')  # optional, for loan repayments

    if not all([user_id, trans_type, amount]):
        return jsonify({'error': 'user_id, type, and amount are required'}), 400

    # Role-based access
    if user.role.lower() == 'chairperson' and user_id != current_user_id:
        return jsonify({'error': 'Chairperson cannot create transactions for other members.'}), 403
    elif user.role.lower() not in ['chairperson', 'treasurer', 'admin']:
        return jsonify({'error': 'You do not have permission to create transactions.'}), 403

    new_trans = Transaction(
        user_id=user_id,
        type=trans_type,
        amount=amount,
        loan_id=loan_id if loan_id else None,
        created_by=current_user_id,
        created_at=datetime.utcnow()
    )
    db.session.add(new_trans)

    # -----------------------------
    # Update balances
    # -----------------------------
    if trans_type == 'deposit':
        saving = Saving.query.filter_by(user_id=user_id).first()
        if not saving:
            saving = Saving(user_id=user_id, total_saved=0)
            db.session.add(saving)
        saving.total_saved += amount

    elif trans_type == 'withdrawal':
        saving = Saving.query.filter_by(user_id=user_id).first()
        if not saving or saving.total_saved < amount:
            return jsonify({'error': 'Insufficient balance for withdrawal.'}), 400
        saving.total_saved -= amount

    elif trans_type == 'loan_payment':
        if not loan_id:
            return jsonify({'error': 'loan_id is required for loan payments.'}), 400
        loan = Loan.query.get(loan_id)
        if not loan or loan.user_id != user_id:
            return jsonify({'error': 'Invalid loan.'}), 404
        loan.amount_paid += amount
        loan.balance = max(0, loan.amount - loan.amount_paid)

    db.session.commit()

    return jsonify({'message': 'Transaction recorded successfully', 'transaction_id': new_trans.transaction_id}), 201



# -----------------------------
    # Notifications
# -----------------------------
    # Notify the member about the transaction
    notif_member = Notification(
        user_id=user_id,
        message=f'{trans_type.capitalize()} of {amount} recorded. New balance: {saving.total_saved if saving else "N/A"}'
    )
    db.session.add(notif_member)

    # Notify the treasurer (assuming treasurer is responsible for all users in SACCO)
    treasurers = User.query.filter_by(role='Treasurer').all()
    for t in treasurers:
        notif_treasurer = Notification(
            user_id=t.user_id,
            message=f'{trans_type.capitalize()} of {amount} for member {user_id} recorded.'
        )
        db.session.add(notif_treasurer)

    db.session.commit()

    return jsonify({'message': 'Transaction recorded successfully', 'transaction_id': new_trans.transaction_id}), 201

# -----------------------------
# Get transactions for a user (with summary)
# -----------------------------
@transaction_bp.route('/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_transactions(user_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role.lower() not in ['treasurer', 'admin', 'chairperson']:
        return jsonify({'error': 'You do not have permission to view transactions.'}), 403

    transactions = Transaction.query.filter_by(user_id=user_id).all()

    # Chairperson sees limited info
    if user.role.lower() == 'chairperson' and user_id != current_user_id:
        results = [{'type': t.type, 'amount': t.amount, 'created_at': t.created_at} for t in transactions]
    else:
        results = [{'transaction_id': t.transaction_id, 'type': t.type, 'amount': t.amount,
                    'loan_id': t.loan_id, 'created_by': t.created_by, 'created_at': t.created_at} for t in transactions]

    # Summary
    deposits = sum(t.amount for t in transactions if t.type == 'deposit')
    withdrawals = sum(t.amount for t in transactions if t.type == 'withdrawal')
    loan_payments = sum(t.amount for t in transactions if t.type == 'loan_payment')

    summary = {
        'total_deposits': deposits,
        'total_withdrawals': withdrawals,
        'total_loan_payments': loan_payments,
        'current_balance': deposits - withdrawals
    }

    return jsonify({'transactions': results, 'summary': summary}), 200


# -----------------------------
# Get all transactions (treasurer/admin)
# -----------------------------
@transaction_bp.route('/all', methods=['GET'])
@jwt_required()
def get_all_transactions():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role.lower() not in ['treasurer', 'admin']:
        return jsonify({'error': 'You do not have permission to view all transactions.'}), 403

    transactions = Transaction.query.all()
    results = [{'transaction_id': t.transaction_id, 'user_id': t.user_id, 'type': t.type,
                'amount': t.amount, 'loan_id': t.loan_id, 'created_by': t.created_by,
                'created_at': t.created_at} for t in transactions]

    return jsonify(results), 200
