# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel Sverige AB (<http://vertel.se>).
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
# odoo.osv was removed in 20.0; the module does not use expression.
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class AccountPaymentLine(models.Model):
    _inherit = 'account.payment.line'
    regulatory_reporting_code = fields.Many2one('regulatory.reporting.code',string="Regulatory Reporting Code")


