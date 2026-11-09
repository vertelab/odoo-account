# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountReport(models.Model):
    _inherit = 'account.report'

    mis_report_id = fields.Many2one(
        comodel_name='mis.report',
        string='Source MIS Report',
        ondelete='set null',
        readonly=True,
        index=True,
        help='The MIS Builder report this one was generated from. Used to make '
             'the conversion idempotent and to trace a report back to its '
             'origin. Empty for hand-made reports.',
    )
