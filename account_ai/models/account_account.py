# -*- coding: utf-8 -*-
"""account.account bär OKF-kontraktet (account_ai).

VARFÖR: kontoplanen är den kunskap AI-kategoriseringen frågar efter — "vilket
konto används för vad?". I dag gissar `account_invoice_ai` konto med en
hårdkodad svensk nyckelordsmap (`_guess_account_from_name`), och
`PLAN_account_invoice_ai.md` konstaterar att `note` på de flesta 4xxx–6xxx-konton
delar samma generiska text och därför är "useless for AI classification".

Källor:
    code   — kontokoden (6540)
    name   — kontonamnet (IT-tjänster)
    note   — den interna anteckningen (vad kontot faktiskt används till)

Den GENERISKA `_okf_body_source()` räcker: `name` tas alltid med, och `note`
är ett Text-fält utan gruppbegränsning. Ingen överridning behövs — till
skillnad från account.move, där innehållet ligger på raderna.

Volymen är ~300–1 500 rader mot account.moves ~50 000+, och konton ändras
sällan. Modellen registreras därför som PRIORITERAD: den driver AI-flöden
och ska inte svälta bakom ett arkiv i cron-kön.

⚠️ `code` är ett Char-fält och ingår INTE i mixinens generiska body (som tar
`name` + HTML/Text). Kroppen överrids därför — utan den blev konceptet
osökbart på kontokoden, vilket är det man skriver när man letar efter ett
konto.
"""

from odoo import fields, models


class AccountAccount(models.Model):
    _name = 'account.account'
    _inherit = ['account.account', 'ai.okf.mixin']

    # OKF-taggar: egen relationstabell (en many2many kan inte ligga på en
    # abstrakt mixin — den ger samma tabell för alla arvande modeller).
    okf_tags = fields.Many2many(
        'ai.okf.tag', 'account_account_okf_tag_rel', 'res_id', 'tag_id',
        string='OKF Tags')

    # ── Källor ───────────────────────────────────────────────────────────
    #
    # `okf_body`  ÖVERRIDEN: `code` är Char och ingår inte i den generiska
    #             defaulten — se `_okf_body_source()` nedan
    # `okf_tags`  generisk: inget taggfält finns på account.account —
    #             listan blir tom, inte fel
    # `okf_links` generisk: `company_ids` (res.company via base_ai),
    #             `tax_ids` (account.tax — bär inte mixinen, hoppas över)

    def _okf_artifact_type(self):
        """Bryggans egen typ (okf-mixin D12)."""
        return 'account_account'

    def _okf_body_source(self):
        """Kontots innehåll: kod + namn + anteckning.

        DEN GENERISKA DEFAULTEN RÄCKER INTE — den tar `name` plus HTML/Text,
        och `code` är ett Char-fält som därför utesluts. Utan överridning blev
        kroppen "IT-tjänster\n\nAnvänds för molntjänster..." utan koden 6540,
        vilket gör kontot osökbart på det man faktiskt skriver när man letar
        efter det (mätt i test 2026-11-12).

        Koden ÄR kontots identitet; namnet är dess betydelse; anteckningen
        säger vad det används till. Alla tre behövs.
        """
        self.ensure_one()
        parts = []
        if self.code:
            parts.append(self.code)
        if self.name:
            parts.append(self.name)
        if self.note:
            parts.append(self.note)
        return '\n\n'.join(p for p in parts if p) or None

    def _okf_summary_source(self):
        """Kontokod + namn — deterministiskt.

        Koden ÄR kontots identitet, och namnet dess betydelse. Ingen LLM
        behövs för att veta det.
        """
        self.ensure_one()
        bits = []
        if self.code:
            bits.append(self.code)
        if self.name:
            bits.append(self.name)
        return ' — '.join(bits) or None

    def _okf_dirty_fields(self):
        """Fält vars ändring gör OKF-fälten inaktuella.

        `active` (18.0: `deprecated`) ingår: ett avaktiverat konto ska
        uppdatera sitt koncept. `account_type` ingår: den säger vad kontot ÄR
        (tillgång, kostnad, moms) och är en del av dess mening för
        AI-kategoriseringen.
        """
        return {'code', 'name', 'note', 'account_type', 'active'}

    def _okf_skip_reason(self):
        """Även ett avaktiverat konto indexeras — det finns kvar i historiken."""
        return None

    # ==================================================================
    # Registrering (okf-mixin D11)
    # ==================================================================

    def _register_hook(self):
        """Registrera account.account — indexerbar OCH prioriterad."""
        res = super()._register_hook()
        okf = self.env['ai.okf.mixin']
        okf._okf_register_indexable('account.account')
        okf._okf_register_priority_indexable('account.account')
        return res
