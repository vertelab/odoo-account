# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    # Field names are part of the contract: they reuse the existing
    # account_account.tagetik_code / tagetik_text columns, so the values
    # already stored in production survive the module replacement.
    tagetik_code = fields.Char(
        string='Tagetik Code',
        copy=False)
    tagetik_text = fields.Char(
        string='Tagetik Text',
        copy=False)
