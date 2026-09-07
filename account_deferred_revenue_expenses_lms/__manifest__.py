# Copyright (C) 2026 Vertel AB (<https://vertel.se>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Deferred Revenue & Expenses: Training (LMS)',
    'version': '18.0.2.4.0',
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

5 sections, 27 slides total (5 quiz questions per section):
- Section 1: Grundläggande periodisering (teori + lagkrav + quiz)
- Section 2: Förutbetalda kostnader — BAS 1710 (bokföring + T-konto + quiz)
- Section 3: Förutbetalda intäkter — BAS 2990 (bokföring + quiz)
- Section 4: Periodisering i Odoo — praktisk guide (demo + övning + quiz)
- Section 5: Så fungerar Odoo-modulen — teknisk guide (arkitektur + wizard + datamodell + quiz)

Includes 8 Mermaid-generated diagrams (rules hierarchy, process flow, compare,
T-account visualization, module architecture, wizard flow, data model, workflow)
and Odoo page builder articles with annotated walkthroughs.
    """,
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
        'data/slide_slides_s5.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
