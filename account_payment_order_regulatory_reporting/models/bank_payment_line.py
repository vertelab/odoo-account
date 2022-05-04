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
from odoo import api, fields, models, _, exceptions
from odoo.osv import expression
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class BankPaymentLine(models.Model):
    _inherit = 'bank.payment.line'
    regulatory_reporting_code = fields.Many2one('regulatory.reporting.code',string="Regulatory Reporting Code")
    
    @api.model
    def create(self, vals):
        _logger.warning("create"*100)
        _logger.warning(f"create{vals }")
        res = super(BankPaymentLine, self).create(vals)
        
        for account_line in res.payment_line_ids:
            if account_line.regulatory_reporting_code:
                _logger.warning(f"{account_line= } , regulatory_reporting = {account_line.regulatory_reporting_code}")
                res.regulatory_reporting_code = account_line.regulatory_reporting_code
                break
        
        if res.currency_id.name != "SEK" and self.env.company.country_code == 'SE' and not res.regulatory_reporting_code and res.amount_company_currency >= 150000:
            error_args = {"line_partner": res.partner_id.name, "line_communication": res.communication,"line_amount_sek":res.amount_company_currency,"line_amount_euro":res.amount_currency,'line_currency':res.currency_id.name}
            raise UserError(_("Regulatory Reporting Code is missing in a line\n\n"
                            "{line_partner} {line_communication} {line_amount_euro}\n\n"
                            "Regulatory Reporting Code is required when the currency is other then SEK ({line_currency}) and when the value ({line_amount_sek}) is greater or equal to 150000 SEK\n\n"
                            "This important when making bank files." ).format(**error_args))
        return res
    


class AccountPaymentLine(models.Model):
    _inherit = 'account.payment.line'
    regulatory_reporting_code = fields.Many2one('regulatory.reporting.code',string="Regulatory Reporting Code")


