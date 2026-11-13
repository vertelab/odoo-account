# -*- coding: utf-8 -*-
"""Tester för account.move-bryggan (account_ai).

Körs med: checkmodule -t -u account_ai (eller odoo --test-enable).

Varje test motsvarar ett scenario i
openspec/changes/account-okf-bridge/specs/account-okf-indexing/spec.md.
"""

from odoo import fields
from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestOkfAccountMove(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'Kund Zeta'})
        cls.account_it = cls.env['account.account'].create({
            'code': '6540', 'name': 'IT-tjänster',
            'account_type': 'expense',
        })
        cls.journal = cls.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', cls.company.id)],
            limit=1)

    def _make_bill(self, state='draft', **vals):
        """Skapa ett leverantörsverifikat med en innehållsrad."""
        move_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': 'Hosting november',
                'account_id': self.account_it.id,
                'price_unit': 10000.0,
                'quantity': 1.0,
            })],
        }
        move_vals.update(vals)
        move = self.env['account.move'].create(move_vals)
        if state == 'posted':
            move.action_post()
        return move

    # ── Kroppen: innehåll, inte kuvert ─────────────────────────────────

    def test_body_has_line_labels_and_account(self):
        """Radetikett och kontokod finns i kroppen (spec: kroppen)."""
        move = self._make_bill()
        body = move._okf_body_source() or ''
        self.assertIn('Hosting november', body)
        self.assertIn('6540', body)
        self.assertIn('IT-tjänster', body)

    def test_body_has_identity(self):
        """Part, datum och belopp finns i kroppen."""
        move = self._make_bill()
        body = move._okf_body_source() or ''
        self.assertIn('Kund Zeta', body)
        self.assertIn('10000', body)

    def test_standard_terms_not_indexed(self):
        """Företagets standardvillkor hamnar INTE i kroppen.

        Två fakturor med samma standardtext ska få olika kroppar — annars
        kollapsar sökindexet och vektorrummet.
        """
        self.company.invoice_terms = '<p>Betalning inom 30 dagar.</p>'
        self.company.terms_type = 'html'
        move_a = self._make_bill(ref='A-1')
        move_b = self._make_bill(ref='B-2')
        body_a = move_a._okf_body_source() or ''
        body_b = move_b._okf_body_source() or ''
        self.assertNotIn('Betalning inom 30 dagar', body_a)
        self.assertNotIn('Betalning inom 30 dagar', body_b)
        self.assertNotEqual(body_a, body_b)

    def test_own_narration_is_indexed(self):
        """En EGEN not i narration-fältet indexeras."""
        self.company.invoice_terms = '<p>Betalning inom 30 dagar.</p>'
        self.company.terms_type = 'html'
        move = self._make_bill()
        move.narration = '<p>Avser konsultarbete i oktober.</p>'
        body = move._okf_body_source() or ''
        self.assertIn('Avser konsultarbete i oktober', body)
        self.assertNotIn('Betalning inom 30 dagar', body)

    def test_body_without_lines_is_not_empty(self):
        """Utan rader byggs kroppen av identiteten — aldrig tom."""
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': self.env['account.journal'].search(
                [('type', '=', 'general')], limit=1).id,
        })
        move.write({'line_ids': [(0, 0, {
            'name': '', 'account_id': self.account_it.id,
            'debit': 0.0, 'credit': 0.0,
        })]})
        body = move._okf_body_source() or ''
        self.assertTrue(body.strip(), 'kroppen får inte vara tom')

    # ── Sammanfattning ─────────────────────────────────────────────────

    def test_summary_is_deterministic(self):
        """Samma oförändrade verifikat ger identisk text två gånger."""
        move = self._make_bill()
        self.assertEqual(move._okf_summary_source(),
                         move._okf_summary_source())
        self.assertTrue(move._okf_summary_source())

    def test_summary_uses_model_source(self):
        """Deterministisk sammanfattning — ingen LLM ('model')."""
        move = self._make_bill()
        _summary, source = move._okf_build_summary(
            move._okf_body_source() or '', 2000)
        self.assertEqual(source, 'model')

    # ── Utkast indexeras (spec: både utkast och bokförda) ──────────────

    def test_draft_is_indexable(self):
        """Ett utkast i fönstret ska INTE avföras."""
        move = self._make_bill()
        self.assertEqual(move.state, 'draft')
        self.assertIsNone(move._okf_skip_reason())

    def test_posted_is_indexable(self):
        """Ett bokfört verifikat i fönstret ska inte avföras."""
        move = self._make_bill(state='posted')
        self.assertEqual(move.state, 'posted')
        self.assertIsNone(move._okf_skip_reason())

    def test_draft_creates_concept(self):
        """Utkast ger ett koncept (spec: Utkast indexeras).

        Rader­texten ligger i konceptets `source_text` (kroppen), inte i
        `summary` — summary är en deterministisk etikett på 1–2 rader.
        `source_text` ingår i `search_vector`, så brödtexten är ändå sökbar
        (verifierat i kärnans hooks.py: GIN-vektorn byggs över summary +
        title + source_text).
        """
        move = self._make_bill()
        concept = move._okf_index_record()
        self.assertTrue(concept)
        self.assertIn('Hosting november', concept.source_text or '')
        self.assertTrue((concept.summary or '').strip())

    def test_concept_updates_after_posting(self):
        """Konceptet speglar bokfört innehåll efter bokning."""
        move = self._make_bill()
        concept = move._okf_index_record()
        self.assertTrue(concept)
        move.action_post()
        move._okf_index_record()
        concept.invalidate_recordset()
        self.assertTrue(concept.title)
        self.assertNotIn('Draft', concept.title or '')

    # ── Avföring ───────────────────────────────────────────────────────

    def test_cancelled_is_skipped(self):
        """Annullerat verifikat avförs med orsak och flaggan rensas."""
        move = self._make_bill(state='posted')
        move.button_cancel()
        self.assertEqual(move._okf_skip_reason(), 'annullerad')

    def test_outside_window_is_skipped(self):
        """Verifikat utanför räkenskapsåret avförs."""
        old_date = fields.Date.subtract(fields.Date.today(), years=3)
        move = self._make_bill(invoice_date=old_date)
        self.assertEqual(move._okf_skip_reason(), 'utanför fönstret')

    def test_window_uses_fiscal_year_not_calendar_year(self):
        """Fönstret följer bolagets räkenskapsår (spec: brutet räkenskapsår).

        Bolag med räkenskapsår maj–april: en verifikation daterad i juni
        ligger i INNEVARANDE räkenskapsår och ska indexeras.
        """
        self.company.fiscalyear_last_day = 30
        self.company.fiscalyear_last_month = '4'  # april
        bounds = self.company.compute_fiscalyear_dates(fields.Date.today())
        mid = bounds['date_from'] + (bounds['date_to'] - bounds['date_from']) / 2
        move = self._make_bill(invoice_date=mid)
        self.assertIsNone(move._okf_skip_reason())
        self.assertTrue(move._okf_in_window())

    def test_skip_clears_dirty_flag(self):
        """Avförd post får okf_dirty = False (blockerar inte kön)."""
        move = self._make_bill(state='posted')
        move.button_cancel()
        move._okf_index_record()
        self.assertFalse(move.okf_dirty)

    # ── Flaggan ────────────────────────────────────────────────────────

    def test_dirty_flag_set_on_content_change(self):
        """Ändring av innehållsfält tänder flaggan."""
        move = self._make_bill()
        move._okf_index_record()
        self.assertFalse(move.okf_dirty)
        move.write({'ref': 'ny referens'})
        self.assertTrue(move.okf_dirty)

    def test_dirty_flag_set_on_line_write_through_move(self):
        """Radändring via move.write tänder flaggan (vanliga UI-vägen)."""
        move = self._make_bill()
        move._okf_index_record()
        self.assertFalse(move.okf_dirty)
        move.write({'invoice_line_ids': [(0, 0, {
            'name': 'Ny rad', 'account_id': self.account_it.id,
            'price_unit': 500.0,
        })]})
        self.assertTrue(move.okf_dirty)

    # ── Registrering ───────────────────────────────────────────────────

    def test_registered_for_indexing(self):
        """account.move finns i den indexerbara listan."""
        self.assertIn('account.move',
                      self.env['ai.okf.mixin']._okf_indexable_models())

    def test_artifact_type_exists(self):
        """Bryggans artefakttyp finns och pekar tillbaka på account_ai."""
        atype = self.env['ai.artifact.type'].search(
            [('name', '=', 'account_move')], limit=1)
        self.assertTrue(atype)
        self.assertEqual(atype.bridge_module, 'account_ai')


@tagged('post_install', '-at_install')
class TestOkfBackfill(common.TransactionCase):
    """Backfill-wizarden: fönstret, idempotensen, kön (spec: Backfill)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'Kund Backfill'})
        cls.account = cls.env['account.account'].create({
            'code': '6543', 'name': 'Backfill-konto',
            'account_type': 'expense',
        })
        cls.journal = cls.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', cls.company.id)],
            limit=1)

    def _bill(self, invoice_date):
        return self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner.id,
            'journal_id': self.journal.id,
            'invoice_date': invoice_date,
            'invoice_line_ids': [(0, 0, {
                'name': 'Backfill-rad',
                'account_id': self.account.id,
                'price_unit': 100.0,
            })],
        })

    def test_default_dates_follow_fiscal_year(self):
        """Förvalda datum matchar bolagets räkenskapsår."""
        wiz = self.env['account.okf.backfill'].create({})
        bounds = self.company.compute_fiscalyear_dates(fields.Date.today())
        self.assertEqual(wiz.date_from, bounds['date_from'])
        self.assertEqual(wiz.date_to, bounds['date_to'])

    def test_backfill_flags_window_only(self):
        """Bara poster i intervallet flaggas (spec: Backfill fyller fönstret)."""
        old = fields.Date.subtract(fields.Date.today(), years=5)
        inside = self._bill(fields.Date.today())
        outside = self._bill(old)
        # Nollställ flaggorna så utfallet är mätbart
        (inside | outside)._write_okf_fields({'okf_dirty': False})

        wiz = self.env['account.okf.backfill'].create({
            'date_from': fields.Date.subtract(fields.Date.today(), months=1),
            'date_to': fields.Date.add(fields.Date.today(), months=1),
        })
        wiz.action_backfill()
        inside.invalidate_recordset()
        outside.invalidate_recordset()
        self.assertTrue(inside.okf_dirty)
        self.assertFalse(outside.okf_dirty)

    def test_backfill_is_idempotent(self):
        """Två körningar ger samma resultat (spec: Backfill körs om)."""
        move = self._bill(fields.Date.today())
        move._write_okf_fields({'okf_dirty': False})

        vals = {
            'date_from': fields.Date.subtract(fields.Date.today(), months=1),
            'date_to': fields.Date.add(fields.Date.today(), months=1),
        }
        self.env['account.okf.backfill'].create(vals).action_backfill()
        first = self.env['account.move'].search_count([('okf_dirty', '=', True)])

        self.env['account.okf.backfill'].create(vals).action_backfill()
        second = self.env['account.move'].search_count([('okf_dirty', '=', True)])

        self.assertEqual(first, second)
        # Inga dubbletter i koncepttabellen för samma nyckel
        move._okf_index_record()
        move._okf_index_record()
        keys = self.env['ai.okf.concept'].search([
            ('concept_key', '=', 'account.move,%s' % move.id),
        ])
        self.assertEqual(len(keys), 1)

    def test_backfill_without_drafts(self):
        """include_drafts=False lämnar utkast orörda."""
        draft = self._bill(fields.Date.today())
        draft._write_okf_fields({'okf_dirty': False})
        wiz = self.env['account.okf.backfill'].create({
            'date_from': fields.Date.subtract(fields.Date.today(), months=1),
            'date_to': fields.Date.add(fields.Date.today(), months=1),
            'include_drafts': False,
        })
        wiz.action_backfill()
        draft.invalidate_recordset()
        self.assertFalse(draft.okf_dirty)
