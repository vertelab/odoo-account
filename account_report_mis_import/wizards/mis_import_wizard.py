# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class MisImportWizard(models.TransientModel):
    _name = 'account.report.mis.import.wizard'
    _description = 'Convert MIS reports to account.report'

    mis_report_ids = fields.Many2many(
        comodel_name='mis.report',
        string='MIS Reports',
        help='Leave empty to convert every MIS report that has no '
             'account.report equivalent yet.',
    )
    dry_run = fields.Boolean(
        string='Dry run',
        default=True,
        help='Report what would be created without writing anything.',
    )
    result_text = fields.Text(string='Result', readonly=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Done')], default='draft')

    def action_convert(self):
        self.ensure_one()
        service = self.env['account.report.mis.import']
        reports = self.mis_report_ids or self.env['mis.report'].search([])

        lines = []
        totals = {'created': 0, 'existing': 0, 'warnings': 0, 'differences': 0}
        for mis_report in reports:
            res = service.convert_report(mis_report, dry_run=self.dry_run)
            label = 'DRY-RUN' if self.dry_run else 'DONE'
            if res['created']:
                totals['created'] += 1
            else:
                totals['existing'] += 1
            totals['warnings'] += len(res['warnings'])
            totals['differences'] += len(res['differences'])
            lines.append(
                '[%s] %-40s lines=%-4d expressions=%-4d warnings=%d differences=%d'
                % (label, mis_report.name[:40], res['lines'],
                   res['expressions'], len(res['warnings']),
                   len(res['differences'])))
            for warning in res['warnings']:
                lines.append('      %s' % warning)
            for diff in res['differences']:
                lines.append('      DIFF %s' % diff)

        lines.append('')
        lines.append('Reports created: %(created)d, already present: '
                     '%(existing)d, warnings: %(warnings)d, differences: '
                     '%(differences)d' % totals)

        self.write({'result_text': '\n'.join(lines), 'state': 'done'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
