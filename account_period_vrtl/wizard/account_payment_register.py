# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    
    def action_create_payments(self):
        for record in self:
            period_id = record.env['account.period'].date2period(record.payment_date)
            # period_by_journal = record.env['account.period']._get_period_by_journal(
            #     record.journal_id, record.payment_date
            # )

            if period_id and period_id.state == 'done':
                raise ValidationError(_(
                    "You have tried to create an payment on a date during a closed period {period_id.name}."
                    "\n Please change the date or open {period_id.name}").format(**locals())
                )

        return super(AccountPaymentRegister, self).action_create_payments()
