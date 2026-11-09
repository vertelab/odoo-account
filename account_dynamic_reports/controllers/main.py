# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
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

    @http.route('/account_dynamic_report/get_drilldown', type='json',
                auth='user', methods=['POST'])
    def get_drilldown(self, report_id, line_id, options=None):
        """Return the move lines behind a report line.

        ``line_id`` is either the numeric ``account.report.line`` id or the
        frontend's string id (``report_line_<id>``). ``options`` carries the
        same date range and column group the figure was rendered with, so the
        list always sums to the displayed value.
        """
        if not report_id or not line_id:
            return {'error': 'report_id and line_id are required', 'move_line_ids': []}

        try:
            report = request.env['account.report'].browse(int(report_id))
            if not report.exists():
                return {'error': f'Report {report_id} not found', 'move_line_ids': []}

            # Accept both 'report_line_42' and 42.
            raw_id = str(line_id)
            if raw_id.startswith('report_line_'):
                raw_id = raw_id[len('report_line_'):]
            line = request.env['account.report.line'].browse(int(raw_id))
            if not line.exists() or line.report_id != report:
                return {'error': f'Line {line_id} does not belong to the report',
                        'move_line_ids': []}

            opts = options or {}
            # The signed amounts carry the engine's own sign (tax_negate for
            # tax_tags, formula negation for account_codes), so the list adds
            # up to the figure the user clicked.
            signed = report._get_line_signed_amounts(line, opts)
            move_lines = request.env['account.move.line']
            for move_line, _amount in signed:
                move_lines |= move_line
            total = sum(amount for _line, amount in signed)

            return {
                'move_line_ids': move_lines.ids,
                'count': len(move_lines),
                'sum': total,
                'action': line._get_drilldown_action(move_lines) if move_lines else False,
            }
        except Exception as e:
            _logger.exception(
                "Error drilling down report %s line %s: %s", report_id, line_id, str(e))
            return {'error': str(e), 'move_line_ids': []}
