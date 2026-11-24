# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # Not stored: a move has many lines with different accounts, so the value
    # is only meaningful for display and search on the move itself.
    tagetik_code = fields.Char(
        string='Tagetik Code',
        related='line_ids.account_id.tagetik_code',
        store=False)
    tagetik_text = fields.Char(
        string='Tagetik Text',
        related='line_ids.account_id.tagetik_text',
        store=False)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # Stored: the line has exactly one account, so the value can be searched
    # and grouped on at line level.
    tagetik_code = fields.Char(
        string='Tagetik Code',
        related='account_id.tagetik_code',
        store=True)
    tagetik_text = fields.Char(
        string='Tagetik Text',
        related='account_id.tagetik_text',
        store=True)


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    tagetik_code = fields.Char(
        string='Tagetik Code',
        copy=False)
    tagetik_text = fields.Char(
        string='Tagetik Text',
        copy=False)
