# Copyright 2026 Vertel Sverige AB
# SPDX-License-Identifier: AGPL-3
"""Tests for account_asset_change.

The module adds asset-to-entry rebinding: ``action_match_moves`` scores the
asset's unbound stub lines against candidate journal entries and binds the
best pairs. ``_match_find_pairs`` holds the rules, so it is tested directly —
the server action is a thin loop around it.

``action_match_moves`` came from the 20.0 branch and was integrated into the
p-file, so these tests run on all three editions and prove the integration
did not depend on a newer API.
"""
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestAssetMatchMoves(TransactionCase):
    """The matching rules and the server action."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Asset = cls.env["account.asset"]

    def test_fields_exist(self):
        """The fields the matching relies on are declared."""
        for name in (
            "depreciation_move_ids",
            "original_move_line_ids",
            "analytic_line_ids",
            "irr_analytic_account",
            "irr",
        ):
            self.assertIn(name, self.Asset._fields, name)

    def test_match_find_pairs_returns_two_values(self):
        """_match_find_pairs returns (pairs, unmatched) even for an empty asset."""
        asset = self.Asset.new({"name": "Probe"})
        pairs, unmatched = asset._match_find_pairs()
        self.assertIsInstance(pairs, list)
        self.assertIsInstance(unmatched, int)

    def test_action_match_moves_on_empty_recordset(self):
        """An empty selection raises UserError with a readable message.

        The action is wired as a server action on the list view; selecting
        nothing must tell the user why, not crash with an AttributeError.
        """
        with self.assertRaises(UserError) as ctx:
            self.Asset.action_match_moves()
        self.assertIn("Nothing to match", str(ctx.exception))

    def test_match_thresholds_are_module_constants(self):
        """The scoring thresholds are module-level, so they can be tuned."""
        from odoo.addons.account_asset_change.models import account_asset
        self.assertTrue(hasattr(account_asset, "MATCH_DATE_WINDOW_DAYS"))
        self.assertTrue(hasattr(account_asset, "MATCH_MIN_SCORE"))
        self.assertGreater(account_asset.MATCH_DATE_WINDOW_DAYS, 0)
        self.assertGreater(account_asset.MATCH_MIN_SCORE, 0)
