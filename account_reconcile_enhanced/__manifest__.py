# Copyright 2026 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Account: Reconcile Enhanced',
    'summary': """Adds enhanced reconciliation tools to the OCA reconcile widget.""",
    'description': '''
Reconcile Enhanced
==================

    Adds enhanced reconciliation tools to the OCA reconcile widget.

    Features:

        - Automation: Scheduled jobs: Bank Transaction Fee, International Transfer Fee, Card Processing Fee.
        - Guided Wizards: Step-by-step dialogs for data entry.
        - UI Integration: Extends 1 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.bank.statement.line, account.move.line, account.reconcile.model, account.reconcile.model.line.
    ''',
    'version': '18.0.1.1.0',
    'license': 'AGPL-3',
    'author': 'Vertel Sverige AB, Odoo Community Association (OCA)',
    'website': 'https://vertel.se/apps/odoo-account/account_reconcile_enhanced',
    'depends': [
        'account_reconcile_oca',
        'account_reconcile_model_oca',
        'account_reconcile_wizard',
    ],
    'excludes': ['account_accountant'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_reconcile_model_fee.xml',
        'wizard/account_reconcile_wizard.xml',
        'wizard/account_auto_reconcile_wizard.xml',
        'views/account_reconcile_views.xml',
    ],
    'assets': {
        'web.assets_backend': [],
    },
}
