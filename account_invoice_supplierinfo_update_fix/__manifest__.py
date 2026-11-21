{
    'name': 'Account: Invoice Supplierinfo Update Fix',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Update the matched vendor pricelist line instead of creating a duplicate.',
    'description': '''
Account: Invoice Supplierinfo Update Fix
========================================

Restores the ``supplierinfo_id`` field in the line list of the
"Check Supplier Infos" wizard (``account_invoice_supplierinfo_update``).

Why
---

The wizard is supposed to update the vendor pricelist line that matches the
bill line, and only create a new one when none exists. The update/create
branch in ``update_supplierinfo()`` already does exactly that, keyed on
``line.supplierinfo_id``.

The field is never rendered in the wizard's line list, though, so the web
client does not hold it in the line record and does not send it back on save.
Every line comes back with ``supplierinfo_id = False``, the write path falls
through to ``create()``, and the wizard duplicates the vendor pricelist line
instead of updating it.

The 17.0 version of the module rendered the field as a hidden column
(``<field name="supplierinfo_id" column_invisible="1" />``). The 18.0
migration (OCA commit 45fcc639a, "[MIG] account_invoice_supplierinfo_update:
Migration to 18.0") dropped it while converting ``<tree>`` to ``<list>``.

What this module does
---------------------

Inherits the wizard form and puts the hidden field back inside the
``line_ids`` list. Nothing else. No Python, no change to the update/create
logic, no change to the matching rule.

The module's own ``decoration-info="not supplierinfo_id"`` marker is left
alone. It was dead for the same reason as the bug (the field was not in the
view, so the expression could never be evaluated) and it stays inert: the
field is rendered as a hidden column, which the web client does not expose to
decoration expressions. The "Pris" column already distinguishes the two cases
— a price for an update, an empty cell for a create.

The module auto-installs with ``account_invoice_supplierinfo_update`` and
should be removed if the fix ever lands upstream.
    ''',
    'depends': ['account_invoice_supplierinfo_update'],
    'data': [
        'views/wizard_update_invoice_supplierinfo_views.xml',
    ],
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_invoice_supplierinfo_update_fix',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'installable': True,
    'auto_install': True,
}
