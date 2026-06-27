# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AccountDynamicReportController(http.Controller):

    @http.route('/account_dynamic_report/get_lines', type='json', auth='user', methods=['POST'])
    def get_report_lines(self, report_id, options=None):
        """Return report lines and columns for rendering in the frontend."""
        if not report_id:
            return {'error': 'No report_id provided', 'lines': [], 'columns': []}

        try:
            report = request.env['account.report'].browse(report_id)
            if not report.exists():
                return {'error': f'Report {report_id} not found', 'lines': [], 'columns': []}

            opts = options or {}
            lines = report._get_lines(opts)
            columns = report._get_columns(opts)

            return {
                'lines': lines,
                'columns': columns,
            }
        except Exception as e:
            _logger.exception("Error generating dynamic report %s: %s", report_id, str(e))
            return {
                'error': str(e),
                'lines': [],
                'columns': [],
            }
