# -*- coding: utf-8 -*-
# Part of Vertel. See LICENSE file for full copyright and licensing details.
{
    'name': 'Account AI — Bridge',
    'version': '1.0',
    'summary': 'OKF-kontraktet på account.move och account.account',
    'category': 'Accounting/Accounting',
    'description': """
        Domänbridge mellan odoo-account och ai_agent_core.

        Lägger ai.okf.mixin på account.move och account.account, så att
        verifikatens innehåll (radetiketter med konto) och kontoplanens
        betydelse indexeras som OKF-koncept och blir sökbara.

        Bryggan äger sina egna artifact_types (account_move, account_account)
        och registrerar modellerna för dirty-indexering — kärnan namnger
        aldrig en domänmodell.

        Beroenden: ENDAST ai_agent_core + account. Ingen koppling till
        account_invoice_ai (PDF/OCR/LLM) — bryggan ska kunna installeras på
        en ren account-installation.
    """,
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_ai',
    'license': 'AGPL-3',
    'depends': [
        'ai_agent_core',
        'account',
    ],
    'data': [
        # #if VERSION >= "20.0"
        'security/ir.access.csv',
        # #else
        'security/ir.model.access.csv',
        # #endif
        'data/account_ai_artifact_types.xml',
        'data/okf_debug_actions.xml',
        'wizard/account_okf_backfill_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
