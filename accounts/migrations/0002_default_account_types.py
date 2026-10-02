from decimal import Decimal

from django.db import migrations


# Registration requires an account type, so a fresh database with none of them
# cannot sign anyone up. Seed the two the README describes; the admin can edit
# or add to them afterwards.
DEFAULT_ACCOUNT_TYPES = [
    {
        'name': 'Savings Account',
        'maximum_withdrawal_amount': Decimal('10000.00'),
        'annual_interest_rate': Decimal('2.00'),
        'interest_calculation_per_year': 4,
    },
    {
        'name': 'Current Account',
        'maximum_withdrawal_amount': Decimal('50000.00'),
        'annual_interest_rate': Decimal('0.50'),
        'interest_calculation_per_year': 1,
    },
]


def create_default_account_types(apps, schema_editor):
    BankAccountType = apps.get_model('accounts', 'BankAccountType')
    # Leave an existing database alone: its types are the operator's choice.
    if BankAccountType.objects.exists():
        return
    BankAccountType.objects.bulk_create(
        BankAccountType(**fields) for fields in DEFAULT_ACCOUNT_TYPES
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_default_account_types, migrations.RunPython.noop
        ),
    ]
