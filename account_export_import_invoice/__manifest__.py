{
    "name": "Account: Export/Import Invoice",
    "version": "1.0",
    "summary": "Export a journal entry to XML and import it back",
    "category": "EDI",
    "author": "Vertel AB",
    "website": "https://vertel.se/apps/odoo-account/account_export_import_invoice",
    "license": "AGPL-3",
    "maintainer": "Vertel AB",
    "repository": "https://github.com/vertelab/odoo-account",
    "description": "Adds an \"Export Account Move\" action on journal entries that writes the entry and its lines to an XML attachment, and an \"Import Account Move\" wizard that recreates the entry from such a file.\n\nThe export covers the invoice header (name, partner, invoice date, journal) and the invoice lines (product, label, account, quantity, price, taxes, subtotal). It is meant for moving individual entries between databases, not for statutory reporting \u2014 use SIE for that.\n\nPorted from 16.0. Odoo 18 already has `account_import_excel` (an Excel import for journal entries); this module adds the XML round trip on top.",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "data/data.xml",
        "wizard/import_account_move_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False
}
