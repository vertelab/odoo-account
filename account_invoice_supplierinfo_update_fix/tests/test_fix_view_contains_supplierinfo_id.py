# Copyright 2026 Vertel Sverige AB
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

"""Verifies that the overlay puts ``supplierinfo_id`` in the line list.

The bug was that ``supplierinfo_id`` was missing from the wizard's line list,
so the web client dropped it on save and every line came back with
``supplierinfo_id = False``, leading to duplicate vendor pricelist lines.

This test checks that the overlay's inherited view contains the hidden
field ``supplierinfo_id`` within the ``line_ids`` list.
"""

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFixViewContainsSupplierinfoId(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.view = cls.env["ir.ui.view"].search([
            ("name", "=", "wizard.update.invoice.supplierinfo.form.fix"),
            ("model", "=", "wizard.update.invoice.supplierinfo"),
        ], limit=1)

    def test_view_contains_supplierinfo_id(self):
        """The inherited arch includes ``supplierinfo_id`` inside ``line_ids`` list."""
        self.assertTrue(
            self.view,
            "The overlay view is missing entirely. Is the module installed?",
        )
        arch = self.view.arch_db or ""
        self.assertIn(
            "supplierinfo_id",
            arch,
            "The overlay view is missing the ``supplierinfo_id`` field.",
        )
        # Ensure it's within the line list, not just somewhere in the view.
        self.assertIn(
            "//field[@name='line_ids']/list/field[@name='product_id']",
            arch,
            "The xpath that adds supplierinfo_id is missing.",
        )
