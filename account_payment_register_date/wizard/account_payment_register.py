# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2026 Vertel AB (<https://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
##############################################################################

from odoo import models, fields, api, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Default payment_date to the invoice's due date when registering payment
        if 'payment_date' in fields_list or 'payment_date' in res:
            # If line_ids was already computed by super(), use them
            line_ids = res.get('line_ids')
            if line_ids:
                # line_ids from default_get for a Many2many is [(6, 0, [id1, id2, ...])]
                ids = []
                for cmd in line_ids:
                    if isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 6:
                        ids = cmd[2]
                        break
                    elif isinstance(cmd, int):
                        ids.append(cmd)
                if ids:
                    lines = self.env['account.move.line'].browse(ids)
                    due_dates = lines.mapped('date_maturity')
                    due_dates = [d for d in due_dates if d]
                    if due_dates:
                        res['payment_date'] = min(due_dates)

        return res
