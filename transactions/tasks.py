from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from celery.decorators import task

from accounts.models import UserBankAccount
from transactions.constants import INTEREST
from transactions.models import Transaction


@task(name="calculate_interest")
@transaction.atomic
def calculate_interest():
    now = timezone.now()
    # interest_start_date keeps the deposit's day, but this runs on the 1st:
    # an account is due from its start month, not its start day.
    next_month = (now + relativedelta(months=+1)).date().replace(day=1)

    accounts = UserBankAccount.objects.filter(
        balance__gt=0,
        interest_start_date__lt=next_month,
        initial_deposit_date__isnull=False
    ).select_related('account_type')

    this_month = now.month

    created_transactions = []
    updated_accounts = []

    for account in accounts:
        if this_month in account.get_interest_calculation_months():
            interest = account.account_type.calculate_interest(
                account.balance
            )
            account.balance += interest
            account.save()

            transaction_obj = Transaction(
                account=account,
                transaction_type=INTEREST,
                amount=interest,
                balance_after_transaction=account.balance
            )
            created_transactions.append(transaction_obj)
            updated_accounts.append(account)

    if created_transactions:
        Transaction.objects.bulk_create(created_transactions)

    if updated_accounts:
        UserBankAccount.objects.bulk_update(
            updated_accounts, ['balance']
        )
