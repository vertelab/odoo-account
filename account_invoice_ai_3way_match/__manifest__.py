{
    'name': 'AI Invoice 3-Way Match Bridge',
    'category': 'Accounting/Accounting',
    'summary': 'Bridge between AI invoice scanning and 3-way purchase matching',
    'description': """
Bridge: AI Invoice Scanning + 3-Way Match
==========================================

Glue module that automatically links AI-scanned vendor bills to purchase
orders so the 3-way match (PO vs receipt vs invoice) works end-to-end.

When both account_invoice_ai and account_3way_match_ce are installed, this
module auto-installs and:

- After AI creates a vendor bill from a scanned PDF, attempts to find
  matching purchase orders for the vendor.
- Matches invoice lines to purchase order lines by product.
- Sets purchase_line_id on matched lines so can_be_paid / release_to_pay
  are computed correctly.
    """,
    'depends': ['account_invoice_ai', 'account_3way_match_ce'],
    'data': [],
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_invoice_ai_3way_match',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'installable': True,
    'auto_install': True,
}
