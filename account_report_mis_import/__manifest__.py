# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Accounting: MIS Report Import',
    'version': '18.0.1.2.4',
    'summary': 'Convert MIS Builder reports to account.report (migration tool)',
    'description': '''
MIS Report Import
=================

A **temporary** migration tool. It converts ``mis.report`` definitions into
``account.report`` definitions so the 4 685 Swedish KPIs across eight modules
can be ported without hand work -- and without anything silently becoming
wrong.

Why a tool and not a rewrite
----------------------------
The Swedish reports are not broken because MIS Builder is bad at budgets.
They are broken because MIS selects on **names** (a tax called ``MP1``, an
account called ``3000``) while ``account.report`` selects on **structure**
(tax tags, account codes as data). Those are different mechanisms, and moving
between them by hand across 2 546 expressions guarantees errors.

The tool therefore converts expression by expression, chooses the engine that
preserves the semantics, and **refuses to guess**: an unrecognised pattern
becomes a domain expression carrying the raw text plus a warning naming report,
line and expression. A wrong amount that nobody notices is worse than a warning.

Scope
-----
Reads:  ``mis.report``, ``mis.report.kpi``, ``mis.report.kpi.expression``,
        ``mis.report.style``
Writes: ``account.report``, ``account.report.line``,
        ``account.report.expression``, ``account.report.column``

It never touches ``account.move`` or ``account.move.line``.

Retirement
----------
When no Swedish module depends on ``mis_builder`` any more this module is set
to ``installable: False`` and kept in the repository as a reference for the
migration it performed.

Measured pattern coverage (see the change's design.md)
------------------------------------------------------
    bal[...] plain            972   -> account_codes
    bal[...] * -1           1 088   -> account_codes, negated formula
    bal[...] with tax filter    6   -> domain
    crd[...]                   45   -> domain
    balp[...]                   1   -> custom + manual review flag
    sum([...])                 409   -> aggregation
    KPI arithmetic              49   -> aggregation
    headings (no expression) 2 139   -> line without expressions
''',
    'category': 'Accounting/Reporting',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-account/account_report_mis_import',
    'license': 'AGPL-3',
    'maintainer': 'Vertel Sverige AB',
    'repository': 'https://github.com/vertelab/odoo-account',
    'depends': ['account', 'mis_builder', 'account_dynamic_reports'],
    'data': [
        'views/mis_import_views.xml',
    ],
    # Retired: the Swedish modules no longer depend on mis_builder, so there is
    # nothing left to convert. Kept in the repository as the reference for the
    # migration it performed -- it is the only place the six conversion rules
    # are written down in code.
    'installable': False,
    'application': False,
    'auto_install': False,
}
