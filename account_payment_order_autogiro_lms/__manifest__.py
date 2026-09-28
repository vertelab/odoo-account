# Copyright (C) 2026 Vertel AB (<https://vertel.se>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account: Payment Order & Autogiro Training (LMS)',
    'version': '18.0.1.0.0',
    'summary': 'Swedish training on the four vendor-bill payment paths in Odoo 18.',
    'category': 'Accounting/Training',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_payment_order_autogiro_lms',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'description': '''
Payment Order & Autogiro Training (LMS)
=======================================

    A Swedish training course on how paying a vendor bill actually behaves in
Odoo 18. The four payment paths look nearly identical in the UI but leave the
bill in different states, which is what the course exists to explain.

    4 sections, 22 slides total (5 quiz questions per section):
        - Section 1: Översikt och beslutsguide (the four paths + quiz)
        - Section 2: Betalorder — vanlig och Autogiro (path a + b + quiz)
        - Section 3: Manuell betalning — datum och Autogiro (path c + d + quiz)
        - Section 4: Bokslut och felsökning (Pågående vs Betald + quiz)

    Includes 5 diagrams (decision guide, order outcome, Pay outcome, state
    diagram, all four paths) and Odoo page builder articles.

    The four paths:

        a) Vanlig betalorder        — posted and reconciled at upload; bill Paid
        b) Betalorder med Autogiro  — nothing posted; bill In Payment until the
                                      bank statement is reconciled
        c) Manuell betalning (Pay)  — payment date below memo, defaulting to the
                                      invoice due date; bill Paid immediately,
                                      entry linked to the bank line later
        d) Manuell betalning med    — no payment and no entry created; bill
           Autogiro (undantag)        flagged and In Payment until reconciliation

    Every statement about the outcome of a path is tied to a named test in
account_payment_order_pending or account_payment_order_autogiro, so the course
describes verified behaviour rather than assumed behaviour. When a payment
module changes, the matching slide must be updated with it.

    This module is training content only — it introduces no models, no fields
and no business logic. SFA-specific behaviour is covered by the companion
course sfa_payment_training_lms in the SFA repository, which auto-installs
with this one.
    ''',
    'depends': [
        'website_slides',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/slide_channel.xml',
        'data/slide_slides_s1.xml',
        'data/slide_slides_s2.xml',
        'data/slide_slides_s3.xml',
        'data/slide_slides_s4.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
