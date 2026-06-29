# Copyright (C) 2026 Vertel AB (<https://vertel.se>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Deferred Revenue & Expenses: Training (LMS)',
    'version': '18.0.2.0.0',
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

4 sections, 17 slides total:
- Section 1: Grundläggande periodisering (teori + lagkrav + quiz)
- Section 2: Förutbetalda kostnader — BAS 1710 (bokföring + quiz)
- Section 3: Förutbetalda intäkter — BAS 2990 (bokföring + quiz)
- Section 4: Periodisering i Odoo — praktisk guide (demo + quiz)

Includes Mermaid-generated diagrams and Odoo page builder articles.
    """,
    'depends': [
        'website_slides',
    ],
    'data': [
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
