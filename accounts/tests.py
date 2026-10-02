from django.test import TestCase

from .forms import UserRegistrationForm
from .models import BankAccountType


class DefaultAccountTypesTests(TestCase):

    def test_migrations_seed_account_types(self):
        names = set(BankAccountType.objects.values_list('name', flat=True))
        self.assertEqual(names, {'Savings Account', 'Current Account'})

    def test_registration_works_on_a_fresh_database(self):
        form = UserRegistrationForm(data={
            'first_name': 'Ada',
            'last_name': 'Lovelace',
            'email': 'ada@example.com',
            'password1': 'a-long-test-passphrase',
            'password2': 'a-long-test-passphrase',
            'account_type': BankAccountType.objects.get(
                name='Savings Account'
            ).pk,
            'gender': 'F',
            'birth_date': '1990-01-01',
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.account.account_type.name, 'Savings Account')
