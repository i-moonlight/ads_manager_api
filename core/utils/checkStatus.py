from django.utils import timezone

def checkStatus(start_date=None, end_date=None, total_spend=None, total_spend_today=None, budget=None, daily_budget=None):
    status = 'ACTIVE'
    current_date = timezone.now().date()

    if start_date and start_date > current_date:
        status = 'SCHEDULED'
    if end_date and end_date < current_date:
        status = 'EXPIRED'
    if total_spend and budget and total_spend >= budget:
        status = 'BUDGET MAXED'
    if total_spend_today and daily_budget and total_spend_today >= daily_budget:
        status = 'BUDGET MAXED'

    return status