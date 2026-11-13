# -*- coding: utf-8 -*-
"""account.move bär OKF-kontraktet (account_ai).

VARFÖR: en faktura är det mest frågade objektet i en redovisningsinstallation,
men den är osökbar. `name` är ett löpnummer ("BILL/2026/11/0001") och det
egentliga innehållet — vad fakturan gäller — ligger i radetiketterna på
`account.move.line`. Ingen av dem syns i ett textsök.

Källor:
    identitet   — nummer, typ, part, datum, belopp
    rader       — etikett + kontokod + kontonamn per rad
    narration   — betalningsvillkor, MEN bara när den avviker från bolagets
                  standardtext (annars identisk på varje faktura)

`_okf_is_ready()` implementeras INTE: både utkast och bokförda indexeras, så
bara `cancel` och fönstret återstår — och båda hanteras av
`_okf_skip_reason()`. En `_okf_is_ready()` som alltid returnerar True vore
död kod.

Okänd fördröjning (dokumenterad i README): en direkt `line.write()` på en rad
tänder ingen flagga, eftersom write-hooken bara ser fält på verifikatet självt.
`move.write({'invoice_line_ids': ...})` — den vanliga UI-vägen — täcks.
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

#: Radtyper som är formatering, inte innehåll. Sektioner och noter bär ingen
#: kunskap om vad fakturan gäller.
_SKIP_DISPLAY_TYPES = ('line_section', 'line_subsection', 'line_note')


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'ai.okf.mixin']

    # OKF-taggar: egen relationstabell (en many2many kan inte ligga på en
    # abstrakt mixin — den ger samma tabell för alla arvande modeller).
    okf_tags = fields.Many2many(
        'ai.okf.tag', 'account_move_okf_tag_rel', 'res_id', 'tag_id',
        string='OKF Tags')

    # ==================================================================
    # Källor — vad mixinen läser
    # ==================================================================

    def _okf_artifact_type(self):
        """Bryggans egen typ (okf-mixin D12)."""
        return 'account_move'

    def _okf_content_lines(self):
        """Raderna som bär innehåll.

        `invoice_line_ids` är en delmängd av `line_ids` (product, section,
        note). För ett verifikat av typen 'entry' finns inga invoice-lines —
        då läses `line_ids`. Båda filtreras på display_type, av samma skäl
        som account_3way_match_ai filtrerar `_billable_lines()`: en sektion
        är formatering.
        """
        self.ensure_one()
        lines = self.invoice_line_ids or self.line_ids
        return lines.filtered(
            lambda line: line.display_type not in _SKIP_DISPLAY_TYPES)

    def _okf_body_source(self):
        """Verifikatets innehåll: identitet + rader (+ egen narration).

        GENERISK DEFAULT RÄCKER INTE: den tar HTML/Text + `name`, vilket för
        account.move ger "BILL/2026/11/0001" plus `narration` — och
        `narration` är företagets betalningsvillkor, identisk på varje
        faktura i bolaget. `search_vector` hade då matchat "dröjsmålsränta"
        på samtliga koncept, och vektorrummet hade kollapsat (kärnan mäter
        cosinus 0,99 för orelaterade par på korta likartade texter).
        """
        self.ensure_one()
        parts = []

        # ── Identitet ──────────────────────────────────────────────────
        if self.name:
            parts.append(self.name)
        if self.move_type and self.move_type != 'entry':
            parts.append(dict(
                self._fields['move_type']._description_selection(self.env),
            ).get(self.move_type, self.move_type))
        if self.partner_id:
            parts.append('Part: %s' % self.partner_id.name)
        if self.invoice_date or self.date:
            parts.append('Datum: %s' % (self.invoice_date or self.date))
        if self.amount_total:
            parts.append('Belopp: %s %s' % (
                self.amount_total, self.currency_id.name or ''))
        if self.ref:
            parts.append('Referens: %s' % self.ref)

        # ── Rader: det egentliga innehållet ────────────────────────────
        line_bits = []
        for line in self._okf_content_lines():
            bits = []
            if line.name:
                bits.append(line.name)
            if line.account_id:
                bits.append('%s %s' % (line.account_id.code or '',
                                       line.account_id.name or ''))
            if line.quantity and line.quantity != 1.0:
                bits.append('%s %s' % (line.quantity, line.product_uom_id.name
                                       or ''))
            amount = line.price_subtotal or line.balance
            if amount:
                bits.append(str(amount))
            rendered = ' — '.join(b.strip() for b in bits if b and b.strip())
            if rendered:
                line_bits.append(rendered)
        if line_bits:
            parts.append('\n'.join(line_bits))

        # ── Narration: ENDAST när den avviker från bolagets standard ───
        #
        # Standardtexten är `company_id.invoice_terms` och sätts av
        # `_compute_narration()`. Att indexera den 50 000 gånger gör
        # sökindexet meningslöst. En användare som skrivit en EGEN not får
        # den däremot indexerad.
        #
        # Jämförelsen normaliseras genom mixinens HTML→text, eftersom
        # samma text kan komma som `<p>a</p>` och `a<br>`.
        if self.narration:
            own = self._okf_html_to_text(self.narration).strip()
            standard = self._okf_html_to_text(
                self.company_id.invoice_terms or '').strip()
            if own and own != standard:
                parts.append(own)

        return '\n\n'.join(p for p in parts if p) or None

    def _okf_summary_source(self):
        """Deterministisk sammanfattning — ingen LLM.

        Part + typ + datum + belopp är det som gör verifikatet identifierbart
        vid sidan av numret. Utan denna föll sammanfattningen tillbaka på en
        LLM-tur per post, och `account.move` är en av de mest indexerade
        modellerna.
        """
        self.ensure_one()
        bits = []
        if self.move_type and self.move_type != 'entry':
            bits.append(dict(
                self._fields['move_type']._description_selection(self.env),
            ).get(self.move_type, self.move_type))
        if self.partner_id:
            bits.append(self.partner_id.name)
        if self.name and self.name != '/':
            bits.append(self.name)
        if self.invoice_date or self.date:
            bits.append(str(self.invoice_date or self.date))
        if self.amount_total:
            bits.append('%s %s' % (self.amount_total,
                                   self.currency_id.name or ''))
        return ' — '.join(b.strip() for b in bits if b) or None

    def _okf_dirty_fields(self):
        """Fält vars ändring gör OKF-fälten inaktuella.

        `invoice_line_ids` ingår: raderna är en del av verifikatets mening.
        Fältet förekommer i `vals` när rader skrivs via `write()` på
        verifikatet (den vanliga UI-vägen), så hooken fångar det fallet.
        En direkt `line.write()` täcks inte — se modulens README.

        Räknare (`amount_residual` uppdateras av betalningar) och
        `payment_state` utesluts: de säger inget om innehållet.
        """
        return {'name', 'ref', 'partner_id', 'move_type', 'journal_id',
                'date', 'invoice_date', 'amount_total', 'narration',
                'invoice_line_ids', 'line_ids'}

    def _okf_skip_reason(self):
        """Annullerat eller utanför fönstret → avför. Annars indexera.

        Fönstret prövas FÖRE allt annat: ett utkast från ett tidigare
        räkenskapsår ska inte ligga och vänta för evigt.
        """
        self.ensure_one()
        if self.state == 'cancel':
            return 'annullerad'
        if not self._okf_in_window():
            return 'utanför fönstret'
        return None

    def _okf_in_window(self):
        """Ligger verifikatet i bolagets AKTUELLA räkenskapsår?

        Fönstret är det räkenskapsår som IDAG tillhör — inte det som
        verifikatets eget datum tillhör.

        FYND (mätt i test 2026-11-12): första versionen skickade
        `self.invoice_date or self.date` till `compute_fiscalyear_dates()`.
        Den funktionen returnerar räkenskapsåret som INNEHÅLLER det datumet,
        så prövningen blev `date_from <= date <= date_to` där `date_to` redan
        var beräknad ur `date` — alltid sant. En verifikation från 2023 ansågs
        ligga i fönstret. En tautologi, inte ett fönster.

        Rätt fråga: "tillhör verifikatet det räkenskapsår som gäller nu?"
        `compute_fiscalyear_dates()` finns i `account` core och läser bolagets
        `fiscalyear_last_day`/`fiscalyear_last_month`, så brutet räkenskapsår
        hanteras gratis.

        Medvetet INGET beroende till account_fiscal_year_vrtl: den hade dragit
        in date_range + cron_tick i en brygga som bara ska indexera, för data
        som core redan kan beräkna.
        """
        self.ensure_one()
        date = self.invoice_date or self.date
        if not date:
            return False
        try:
            bounds = self.company_id.compute_fiscalyear_dates(
                fields.Date.context_today(self))
        except Exception as e:  # noqa: BLE001
            # Fail-closed: kan fönstret inte beräknas avförs posten.
            # Ett saknat svar får aldrig tolkas som "indexera".
            _logger.warning(
                'account_ai: kunde inte beräkna räkenskapsår för %s,%s: %s',
                self._name, self.id, e)
            return False
        return bounds['date_from'] <= date <= bounds['date_to']

    # ==================================================================
    # Registrering (okf-mixin D11)
    # ==================================================================

    def _register_hook(self):
        """Registrera account.move för dirty-indexering.

        Registrering, inte överridning: `_okf_indexable_models()` är
        `@api.model` på en ABSTRAKT modell — en överridning här hade ingen
        verkan på cronen (mätt i kärnan 2026-09-22).
        """
        res = super()._register_hook()
        self.env['ai.okf.mixin']._okf_register_indexable('account.move')
        return res
