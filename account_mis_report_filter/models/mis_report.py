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
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('canceled', 'Canceled')],
        default='draft')

    @api.model
    def _default_user(self):
        return self.env.context.get('user_id', self.env.user.id)

    user_id = fields.Many2one('res.users', 'Responsible', default=_default_user)

    def do_confirm(self):
        for record in self:
            record.state = "confirmed"

    def do_draft(self):
        for record in self:
            record.state = "draft"

    def do_done(self):
        for record in self:
            record.state = "done"

    def do_cancel(self):
        for record in self:
            record.state = "canceled"
