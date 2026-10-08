{
    'name': 'Account: 3-Way Match AI',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'AI-driven 3-way matching of vendor bills against purchase orders.',
    'description': '''
3-Way Match AI
==============

    Matches vendor bill lines to purchase order lines with an AI coworker and
        reports similarities and anomalies (price deviation, quantity
        deviation, product conflict, duplicates).

    The coworker only links invoice lines to purchase order lines; the
        release-to-pay state is then computed by account_3way_match_ce.

    Features:

        - AI Coworker: matches bill lines and reports anomalies.
        - Extends Odoo: Builds on account.move, account.move.line.
    ''',
    'depends': ['ai_agent_core', 'account_3way_match_ce'],
    'data': [
        'data/3way_match_skills.xml',
        'data/3way_match_coworker.xml',
    ],
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_3way_match_ai',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'installable': True,
    'auto_install': False,
}
