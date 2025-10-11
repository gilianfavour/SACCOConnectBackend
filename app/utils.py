from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from app.models.savingModel import Saving
from app.models.loanModal import Loan

# -----------------------------
# Get trends for daily, weekly, monthly
# -----------------------------
def get_trends(model, user_filter=None, period='daily'):
    """
    Returns aggregated sums for a model (Saving or Loan) over a given period.
    :param model: SQLAlchemy model (Saving or Loan)
    :param user_filter: SQLAlchemy filter expression (e.g., Saving.user_id == x)
    :param period: 'daily', 'weekly', or 'monthly'
    :return: dict {date_label: sum_amount}
    """
    now = datetime.utcnow()
    query = db.session.query(
        func.date_trunc('day', model.created_at).label('day'),
        func.sum(model.amount).label('total')
    )

    if user_filter is not None:
        query = query.filter(user_filter)

    if period == 'daily':
        start_date = now - timedelta(days=7)
        query = query.filter(model.created_at >= start_date)
        group_by_expr = func.date_trunc('day', model.created_at)
    elif period == 'weekly':
        start_date = now - timedelta(weeks=4)
        query = query.filter(model.created_at >= start_date)
        group_by_expr = func.date_trunc('week', model.created_at)
    elif period == 'monthly':
        start_date = now - timedelta(days=365)
        query = query.filter(model.created_at >= start_date)
        group_by_expr = func.date_trunc('month', model.created_at)
    else:
        raise ValueError('Invalid period')

    results = query.group_by(group_by_expr).order_by(group_by_expr).all()

    trends = {r.day.strftime('%Y-%m-%d'): float(r.total) for r in results}
    return trends

# -----------------------------
# Get alerts for overdue loans or milestone savers
# -----------------------------
def get_alerts(sacco_id=None, user_filter=None):
    """
    Returns alerts based on overdue loans or milestone savings.
    :param sacco_id: filter by SACCO (for Chairperson/Treasurer)
    :param user_filter: filter by individual user
    :return: list of alert dicts
    """
    from app.models.loanModal import Loan
    from app.models.savingModel import Saving
    from app.models.userModel import User

    alerts = []

    # Overdue loans
    loan_query = Loan.query
    if sacco_id:
        loan_query = loan_query.filter_by(sacco_id=sacco_id)
    if user_filter:
        loan_query = loan_query.filter(user_filter)
    overdue_loans = loan_query.filter(Loan.status == 'pending', Loan.due_date < datetime.utcnow()).all()

    for loan in overdue_loans:
        alerts.append({
            'type': 'overdue_loan',
            'loan_id': loan.loan_id,
            'user_id': loan.user_id,
            'message': f'Loan {loan.loan_id} for {User.query.get(loan.user_id).name} is overdue!'
        })

    # Milestone savings (example: saved over 1000 units)
    saving_query = Saving.query
    if sacco_id:
        saving_query = saving_query.filter_by(sacco_id=sacco_id)
    if user_filter:
        saving_query = saving_query.filter(user_filter)
    milestone_savers = db.session.query(
        Saving.user_id, func.sum(Saving.amount).label('total_saved')
    ).group_by(Saving.user_id).having(func.sum(Saving.amount) >= 1000).all()

    for saver in milestone_savers:
        alerts.append({
            'type': 'milestone_saver',
            'user_id': saver.user_id,
            'message': f'{User.query.get(saver.user_id).name} reached a saving milestone of {float(saver.total_saved)}!'
        })

    return alerts
