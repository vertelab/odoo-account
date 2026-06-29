# Copyright (C) 2026 Vertel AB (<https://vertel.se>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Deferred Revenue & Expenses: Training (LMS)',
    'version': '18.0.1.0.0',
    'summary': 'Swedish periodization training via website_slides',
    'category': 'Accounting/Training',
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'description': """
Deferred Revenue & Expenses LMS
===============================
Training material delivered as website_slides courses.

Topics:
- Förutbetalda kostnader (BAS 1710)
- Förutbetalda intäkter (BAS 2990)
- Periodisering enligt BFL och BFNAR
- Using the Deferred Revenue & Expenses module in Odoo
    """,
    'depends': [
        'account_deferred_revenue_expenses',
        'website_slides',
    ],
    'data': [
        'data/slide_channel.xml',
        'data/slide_slides_basics.xml',
        'data/slide_slides_expense.xml',
        'data/slide_slides_income.xml',
        'data/slide_slides_odoo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
