import datetime
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from accounts.models import BankAccountType, User, UserBankAccount
from transactions.constants import INTEREST
from transactions.models import Transaction
from transactions.tasks import calculate_interest


class CalculateInterestTests(TestCase):
    # 12% a year, credited monthly: 1% of 1000.00 is 10.00 each month.
    NOW = datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc)

    def setUp(self):
        self.account_type = BankAccountType.objects.create(
            name='Monthly',
            maximum_withdrawal_amount=Decimal('1000.00'),
            annual_interest_rate=Decimal('12.00'),
            interest_calculation_per_year=12,
        )

    def make_account(self, number, interest_start_date):
        user = User.objects.create_user(
            email=f'user{number}@example.com', password='unused'
        )
        return UserBankAccount.objects.create(
            user=user,
            account_type=self.account_type,
            account_no=number,
            gender='F',
            balance=Decimal('1000.00'),
            initial_deposit_date=datetime.date(2026, 1, 1),
            interest_start_date=interest_start_date,
        )

    def run_task(self):
        with mock.patch('django.utils.timezone.now', return_value=self.NOW):
            calculate_interest()

    def test_interest_is_paid_once_the_start_date_has_passed(self):
        account = self.make_account(1, datetime.date(2026, 3, 1))

        self.run_task()

        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal('1010.00'))
        interest = Transaction.objects.get(account=account)
        self.assertEqual(interest.transaction_type, INTEREST)
        self.assertEqual(interest.amount, Decimal('10.00'))
        self.assertEqual(interest.balance_after_transaction, Decimal('1010.00'))

    def test_no_interest_before_the_start_date(self):
        # June is one of this account's interest months, but its start is next year.
        account = self.make_account(2, datetime.date(2027, 1, 1))

        self.run_task()

        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal('1000.00'))
        self.assertFalse(Transaction.objects.filter(account=account).exists())
