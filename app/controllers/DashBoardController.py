from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.userModel import User
from app.models.saccoModel import Sacco
from app.models.savingModel import Saving
from app.models.loanModal import Loan
from app.models.transactionModel import Transaction
from app.models.notificationModel import Notification
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from app.utils import get_trends, get_alerts

dashboard_bp = Blueprint('dashboard_bp', __name__)

# -----------------------------
# Helper function for trend data
# -----------------------------
def get_trends(model, user_filter=None, period='daily'):
    today = datetime.utcnow()

    if period == 'daily':
        date_func = func.date(model.created_at)
        start_date = today - timedelta(days=30)  # last 30 days
    elif period == 'weekly':
        date_func = func.strftime('%Y-%W', model.created_at)  # Year-Week number
        start_date = today - timedelta(weeks=12)  # last 12 weeks
    elif period == 'monthly':
        date_func = func.strftime('%Y-%m', model.created_at)  # Year-Month
        start_date = today - timedelta(days=365)  # last 12 months
    else:
        return []

    query = db.session.query(
        date_func.label('period'),
        func.sum(model.amount).label('total')
    ).filter(model.created_at >= start_date)

    if user_filter is not None:
        query = query.filter(user_filter)

    query = query.group_by('period').order_by('period')
    return [{'period': row.period, 'total': float(row.total)} for row in query.all()]

# -----------------------------
# Dashboard Overview with aggregates + alerts
# -----------------------------
@dashboard_bp.route('/overview', methods=['GET'])
@jwt_required()
def dashboard_overview():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role.lower() in ['chairperson', 'treasurer']:
        # -----------------------------
        # SACCO-level overview
        # -----------------------------
        total_saccos = Sacco.query.count()
        total_users = User.query.filter_by(sacco_id=user.sacco_id).count()
        total_savings = db.session.query(func.sum(Saving.amount)).filter_by(sacco_id=user.sacco_id).scalar() or 0
        total_loans = db.session.query(func.sum(Loan.amount)).filter_by(sacco_id=user.sacco_id).scalar() or 0

        # Trends
        trends = {}
        for period in ['daily', 'weekly', 'monthly']:
            trends[f'savings_{period}'] = get_trends(Saving, user_filter=(Saving.sacco_id == user.sacco_id), period=period)
            trends[f'loans_{period}'] = get_trends(Loan, user_filter=(Loan.sacco_id == user.sacco_id), period=period)

        # Top savers and borrowers
        top_savers_query = db.session.query(
            Saving.user_id, func.sum(Saving.amount).label('total_saved')
        ).filter_by(sacco_id=user.sacco_id).group_by(Saving.user_id).order_by(desc('total_saved')).limit(5).all()

        top_savers = [{
            'user_id': s.user_id,
            'name': User.query.get(s.user_id).name,
            'total_saved': float(s.total_saved)
        } for s in top_savers_query]

        top_borrowers_query = db.session.query(
            Loan.user_id, func.sum(Loan.amount).label('total_loaned')
        ).filter_by(sacco_id=user.sacco_id).group_by(Loan.user_id).order_by(desc('total_loaned')).limit(5).all()

        top_borrowers = [{
            'user_id': l.user_id,
            'name': User.query.get(l.user_id).name,
            'total_loaned': float(l.total_loaned)
        } for l in top_borrowers_query]

        # Pending loans
        pending_loans = Loan.query.filter_by(sacco_id=user.sacco_id, status='pending').count()

        # Recent transactions
        recent_transactions = Transaction.query.filter_by(sacco_id=user.sacco_id).order_by(Transaction.created_at.desc()).limit(10).all()
        recent_transactions_list = [{
            'transaction_id': t.transaction_id,
            'user_id': t.user_id,
            'amount': float(t.amount),
            'type': t.type,
            'created_at': str(t.created_at)
        } for t in recent_transactions]

        # Notifications
        notifications = Notification.query.filter_by(user_id=current_user_id).order_by(Notification.created_at.desc()).limit(10).all()
        notifications_list = [{
            'notification_id': n.notification_id,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': str(n.created_at)
        } for n in notifications]

        # Alerts: overdue loans or milestone savers
        alerts = get_alerts(user.sacco_id)

        return jsonify({
            'role': user.role,
            'sacco_id': user.sacco_id,
            'total_saccos': total_saccos,
            'total_users': total_users,
            'total_savings': float(total_savings),
            'total_loans': float(total_loans),
            'trends': trends,
            'top_savers': top_savers,
            'top_borrowers': top_borrowers,
            'pending_loans': pending_loans,
            'recent_transactions': recent_transactions_list,
            'notifications': notifications_list,
            'alerts': alerts
        }), 200

    else:
        # -----------------------------
        # Personalized user overview
        # -----------------------------
        user_savings = db.session.query(func.sum(Saving.amount)).filter_by(user_id=current_user_id).scalar() or 0
        user_loans = db.session.query(func.sum(Loan.amount)).filter_by(user_id=current_user_id).scalar() or 0

        trends = {}
        for period in ['daily', 'weekly', 'monthly']:
            trends[f'savings_{period}'] = get_trends(Saving, user_filter=(Saving.user_id == current_user_id), period=period)
            trends[f'loans_{period}'] = get_trends(Loan, user_filter=(Loan.user_id == current_user_id), period=period)

        user_transactions = Transaction.query.filter_by(user_id=current_user_id).order_by(Transaction.created_at.desc()).limit(10).all()
        transactions_list = [{
            'transaction_id': t.transaction_id,
            'amount': float(t.amount),
            'type': t.type,
            'created_at': str(t.created_at)
        } for t in user_transactions]

        notifications = Notification.query.filter_by(user_id=current_user_id).order_by(Notification.created_at.desc()).limit(10).all()
        notifications_list = [{
            'notification_id': n.notification_id,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': str(n.created_at)
        } for n in notifications]

        # Alerts for individual users
        alerts = get_alerts(user_filter=current_user_id)

        return jsonify({
            'role': user.role,
            'total_savings': float(user_savings),
            'total_loans': float(user_loans),
            'trends': trends,
            'recent_transactions': transactions_list,
            'notifications': notifications_list,
            'alerts': alerts
        }), 200