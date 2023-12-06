from openerp import models, fields, api, _
import logging
from odoo.exceptions import UserError
from collections import defaultdict

import base64
from lxml import etree

# ~ from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class MisReportInstance(models.Model):
    _inherit = 'mis.report.instance'
    
    active = fields.Boolean(default=True)
    
    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    user_id = fields.Many2one('res.users', 'Responsible', default=_default_user)
    
class MisReport(models.Model):
    _inherit = 'mis.report'
    
    active = fields.Boolean(default=True)
    
# ~ class MisReportInstance(models.Model):
    # ~ _inherit = 'mis.report.instance'
    
    # ~ active = fields.Boolean(default=True)


