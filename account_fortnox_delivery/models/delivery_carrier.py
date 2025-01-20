# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import logging
import json
import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

BASE_URL = 'https://api.fortnox.se'


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    fortnox_url = fields.Char()
    fortnox_code = fields.Char()
    fortnox_description = fields.Char()

