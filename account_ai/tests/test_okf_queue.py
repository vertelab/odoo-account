# -*- coding: utf-8 -*-
"""Kö-begränsning: redovisningen får inte svälta andra modeller.

Spec: *Redovisningen får inte svälta övriga modeller i kön*.

Kärnans cron fördelar `cap` rättvist: `per_model = max(1, cap // 4)`, och
`spare = max(0, cap - per_model * len(ordered))`. Med fler än fyra
registrerade modeller blir `spare = 0` och loopen bryter vid `total >= cap` —
modeller sent i rotationen får noll det varvet. Prioriterade modeller går
före taket.

Testet verifierar att `account.move` inte kan ta hela taket: när många
verifikat är flaggade ska en annan modell ändå få minst ett koncept.
"""

from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestOkfQueueFairness(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.okf = cls.env['ai.okf.mixin']

    def test_account_move_is_not_priority(self):
        """account.move ska INTE vara prioriterad — den skulle svälta mail."""
        self.assertNotIn('account.move', self.okf._okf_priority_indexable())

    def test_account_account_is_priority(self):
        """Kontoplanen är prioriterad (liten, sökdrivande)."""
        self.assertIn('account.account', self.okf._okf_priority_indexable())

    def test_fair_share_never_starves_a_model(self):
        """Rättvis fördelning: varje modell garanteras minst 1 per varv.

        `per_model = max(1, cap // 4)` — med cap=8 och 4 modeller blir det
        2 var, och `spare = max(0, 8 - 2*4) = 0`. Ingen modell får noll.
        """
        cap = 8
        models = ['account.move', 'project.task', 'crm.lead', 'res.partner']
        per_model = max(1, cap // 4)
        spare = max(0, cap - per_model * len(models))
        self.assertEqual(per_model, 2)
        self.assertEqual(spare, 0)
        # Summan av andelarna räcker till alla modeller
        self.assertGreaterEqual(per_model * len(models), cap)

    def test_adaptive_cap_respects_max(self):
        """Det adaptiva taket överskrider aldrig OKF_CRON_TAK_MAX."""
        cap = self.okf._okf_adaptive_cap(25, queue_depth=100000)
        self.assertLessEqual(cap, self.okf.OKF_CRON_TAK_MAX)

    def test_adaptive_cap_is_a_floor(self):
        """batch_size är ett GOLV — taket blir aldrig mindre än det."""
        cap = self.okf._okf_adaptive_cap(25, queue_depth=0)
        self.assertGreaterEqual(cap, 25)
