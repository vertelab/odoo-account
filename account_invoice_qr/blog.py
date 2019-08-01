# -*- coding: utf-8 -*-
##############################################################################
#
# Odoo, Open Source Enterprise Resource Management Solution, third party addon
# Copyright (C) 2019- Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import api, fields, models,_
from odoo import http
from odoo.http import request
from datetime import timedelta

import logging
_logger = logging.getLogger(__name__)

import traceback

# ~ class EventEvent(models.Model):
    # ~ """Event"""
    # ~ _inherit = 'event.event'
    # ~ short_desc = fields.Text(string="Kortbeskrivning")
    
    # ~ @api.model
    # ~ def _default_event_mail_ids(self):
        # ~ return [(0, 0, {
            # ~ 'interval_unit': 'now',
            # ~ 'interval_type': 'after_sub',
            # ~ 'template_id': self.env.ref('event.event_subscription')
        # ~ })]

# ~ class EventRegistration(models.Model):
    # ~ _inherit = 'event.registration'

    # ~ address = fields.Char(string='Address')
    # ~ note = fields.Char(string='Note')



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
