# -*- coding: utf-8 -*-
"""Backfill-wizard: flagga verifikat i fönstret för OKF-indexering.

VARFÖR EN WIZARD OCH INTE EN MIGRATION (design Beslut 6):

  Odoo initierar en ny Boolean-kolumn till NULL, inte False
  (`_init_column`: `necessary = (value is not None) if field.type != 'boolean'
  else value`). `okf_dirty` sätts dessutom till False på nyskapade poster av
  `_write_okf_fields`, medan befintliga rader står kvar som NULL. En domän på
  `[('okf_dirty', '=', True)]` fångar därför INTE historiken — och en bred
  `UPDATE ... SET okf_dirty = TRUE` vore fel väg: den skriver förbi både
  flush och mixinens låsordning.

  Wizarden använder `_set_okf_dirty()` — mixinens publika väg, som flushar,
  tar radlås i stigande id-ordning (T/12475) och skriver SQL.

  En `post_init_hook` hade gjort installationen till en tidsinställd bomb på
  en kunddatabas med 100 000 verifikat. Backfill ska vara ett medvetet val.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountOkfBackfill(models.TransientModel):
    _name = 'account.okf.backfill'
    _description = 'Backfill OKF-indexering'

    company_id = fields.Many2one(
        'res.company', string='Bolag', required=True,
        default=lambda self: self.env.company)
    date_from = fields.Date(string='Från datum', required=True)
    date_to = fields.Date(string='Till datum', required=True)
    include_drafts = fields.Boolean(
        string='Inkludera utkast', default=True,
        help='Utkast är arbetet användaren gör just nu och indexeras som '
             'standard. Stäng av för att bara flagga bokförda verifikat.')

    @api.model
    def default_get(self, fields_list):
        """Förval ur bolagets AKTUELLA räkenskapsår.

        Samma källa som `_okf_in_window()`: `compute_fiscalyear_dates()` i
        account core. Inget beroende till account_fiscal_year_vrtl.
        """
        res = super().default_get(fields_list)
        company = self.env.company
        if 'date_from' in fields_list or 'date_to' in fields_list:
            try:
                bounds = company.compute_fiscalyear_dates(fields.Date.today())
            except Exception as e:  # noqa: BLE001
                _logger.warning(
                    'account_ai: kunde inte beräkna räkenskapsår: %s', e)
            else:
                res.setdefault('date_from', bounds['date_from'])
                res.setdefault('date_to', bounds['date_to'])
        return res

    def action_backfill(self):
        """Flagga verifikaten i intervallet — idempotent."""
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('Från-datum måste vara före till-datum.'))

        states = ['draft', 'posted'] if self.include_drafts else ['posted']
        moves = self.env['account.move'].search([
            ('state', 'in', states),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ])
        if not moves:
            raise UserError(_(
                'Inga verifikat i intervallet %(from)s – %(to)s.',
                from_=self.date_from, to=self.date_to))

        before = self.env['account.move'].search_count([
            ('okf_dirty', '=', True),
            ('company_id', '=', self.company_id.id),
        ])

        # Mixinens publika väg: flush → lås i id-ordning → SQL.
        # Aldrig egen UPDATE (design Beslut 6).
        moves._set_okf_dirty()

        after = self.env['account.move'].search_count([
            ('okf_dirty', '=', True),
            ('company_id', '=', self.company_id.id),
        ])
        # Idempotensen: `TRUE` på en redan `TRUE` rad är en no-op, så
        # `after - before` kan vara mindre än antalet träffar.
        newly = after - before
        _logger.info(
            'account_ai backfill: %s verifikat flaggade (%s nya i kön, %s '
            'redan flaggade), intervall %s–%s',
            len(moves), newly, len(moves) - newly,
            self.date_from, self.date_to)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Backfill klar'),
                'message': _(
                    '%(total)s verifikat flaggade (%(new)s nya i kön).',
                    total=len(moves), new=newly),
                'type': 'success',
                'sticky': False,
            },
        }
