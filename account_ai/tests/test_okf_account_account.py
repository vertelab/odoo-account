# -*- coding: utf-8 -*-
"""Tester för account.account-bryggan (account_ai).

Kontoplanen är den kunskap AI-kategoriseringen frågar efter: "vilket konto
används för vad?". Testerna verifierar att kontokod, namn och anteckning
faktiskt når konceptet.
"""

from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestOkfAccountAccount(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account = cls.env['account.account'].create({
            'code': '6541',
            'name': 'IT-tjänster test',
            'account_type': 'expense',
            'note': 'Används för molntjänster, hosting och programvarulicenser.',
        })

    def test_body_has_code_name_and_note(self):
        """Kod, namn och anteckning finns i kroppen (spec: kontoplanen)."""
        body = self.account._okf_body_source() or ''
        self.assertIn('6541', body)
        self.assertIn('IT-tjänster test', body)
        self.assertIn('molntjänster', body)

    def test_body_without_note_is_not_empty(self):
        """Konto utan anteckning byggs av kod + namn — aldrig tomt."""
        account = self.env['account.account'].create({
            'code': '6542', 'name': 'Utan not', 'account_type': 'expense',
        })
        body = account._okf_body_source() or ''
        self.assertTrue(body.strip())
        self.assertIn('6542', body)
        self.assertIn('Utan not', body)

    def test_summary_is_code_and_name(self):
        """Sammanfattningen är kod + namn, deterministiskt."""
        summary = self.account._okf_summary_source()
        self.assertEqual(summary, '6541 — IT-tjänster test')
        self.assertEqual(summary, self.account._okf_summary_source())

    def test_summary_uses_model_source(self):
        """Ingen LLM behövs ('model')."""
        _summary, source = self.account._okf_build_summary(
            self.account._okf_body_source() or '', 2000)
        self.assertEqual(source, 'model')

    def test_deprecated_account_still_indexed(self):
        """Ett avaktiverat konto indexeras — det finns kvar i historiken."""
        self.assertIsNone(self.account._okf_skip_reason())
        self.account.deprecated = True
        self.assertIsNone(self.account._okf_skip_reason())

    def test_deprecated_is_dirty_field(self):
        """Avaktivering tänder flaggan."""
        self.account._okf_index_record()
        self.assertFalse(self.account.okf_dirty)
        self.account.deprecated = True
        self.assertTrue(self.account.okf_dirty)

    def test_note_change_is_dirty_field(self):
        """Ändrad anteckning tänder flaggan."""
        self.account._okf_index_record()
        self.assertFalse(self.account.okf_dirty)
        self.account.note = 'Ny beskrivning.'
        self.assertTrue(self.account.okf_dirty)

    def test_concept_created(self):
        """Kontot ger ett koncept med anteckningen i sammanhanget."""
        concept = self.account._okf_index_record()
        self.assertTrue(concept)
        self.assertIn('6541', concept.title or '')

    def test_artifact_type_uses_accounting_retention(self):
        """Typen bär retention_purpose 'accounting' (första bryggan som gör)."""
        atype = self.env['ai.artifact.type'].search(
            [('name', '=', 'account_account')], limit=1)
        self.assertTrue(atype)
        self.assertEqual(atype.bridge_module, 'account_ai')
        self.assertEqual(atype.okf_contract.get('retention_purpose'),
                         'accounting')

    def test_registered_and_prioritized(self):
        """Kontoplanen är indexerbar OCH prioriterad (liten, sökdrivande)."""
        okf = self.env['ai.okf.mixin']
        self.assertIn('account.account', okf._okf_indexable_models())
        self.assertIn('account.account', okf._okf_priority_indexable())
