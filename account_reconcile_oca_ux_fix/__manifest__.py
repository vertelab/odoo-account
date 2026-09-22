{
    'name': 'Account Reconcile OCA UX Fix',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_reconcile_oca_ux_fix',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Behåll kundfiltret i Reconcile-fliken efter Manual operation',
    'description': """
Account Reconcile OCA UX Fix
============================

Åtgärdar T/11503: kundfiltret i fliken Reconcile nollställs när man varit i
fliken Manual operation och går tillbaka.

Rotorsak (belagd i källkoden 2026-09-16)
----------------------------------------
OCA:s ``ReconcileController`` (account_reconcile_oca) åsidosätter sin förälders
``getLocalState`` med en snävare variant som bara exporterar ``selectedRecordId``.
Föräldern ``KanbanController`` exporterar ``modelState`` — och sökfiltret bor i
``searchModel`` som ``WithSearch`` exporterar som *global* state.

Vid återgång till Reconcile-fliken kör ``reloadFormController()``
``model.root.load()`` utan att sökfiltret appliceras igen, eftersom det inte
finns i den lokala staten.

Fix
---
Patchen utökar ``getLocalState`` att även exportera ``searchModel``, så filtret
bevaras över flikbytet. Implementerad som en ``patch()`` på komponentprototypen
— OCA:s källkod redigeras inte, så fixen överlever OCA-uppdateringar.

Referens: T/11503 (SFA Sverige AB)
    """,
    'depends': ['account_reconcile_oca'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'account_reconcile_oca_ux_fix/static/src/js/reconcile_controller_patch.esm.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
