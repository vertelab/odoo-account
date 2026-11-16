import logging
import numpy_financial as npf
from datetime import date
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from math import copysign

from odoo import api, Command, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, formatLang
from odoo.tools.date_utils import end_of

_logger = logging.getLogger(__name__)

#: Matching thresholds used by ``action_match_moves``.  An entry is only a
#: candidate when it touches both depreciation accounts, carries exactly the
#: line's amount, and is dated within this window of the line date.
MATCH_DATE_WINDOW_DAYS = 45
MATCH_MIN_SCORE = 40


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    depreciation_move_ids = fields.One2many('account.move.line', 'asset_id', string='Depreciation Lines')
    original_move_line_ids = fields.Many2many(comodel_name='account.move.line', relation='asset_move_line_rel', column1='asset_id', column2='line_id', string='Journal Items', copy=False)

    analytic_line_ids = fields.One2many(comodel_name="account.analytic.line", compute="_compute_analytic_line_ids")
    analytic_line_count = fields.Integer(compute="_compute_analytic_line_count")
    account_move_count = fields.Integer(compute="_compute_account_move_count")
    irr_analytic_account = fields.Many2one(comodel_name="account.analytic.account",help="Analytic account to track income and expenses related to this asset.")
    irr = fields.Float(compute="_compute_irr",help="Internal rate of return calculated by cash flow.")

    account_asset_id = fields.Many2one(
        comodel_name='account.account',
        string='Fixed Asset Account',
        compute='_compute_account_asset_id',
        help="Account used to record the purchase of the asset at its original price.",
        store=True, readonly=False,
        check_company=True,
        domain="[('account_type', '!=', 'off_balance')]",
    )

    @api.depends('account_depreciation_id', 'account_depreciation_expense_id', 'original_move_line_ids')
    def _compute_account_asset_id(self):
        for record in self:
            if record.original_move_line_ids:
                if len(record.original_move_line_ids.account_id) > 1:
                    raise UserError(_("All the lines should be from the same account"))
                record.account_asset_id = record.original_move_line_ids.account_id
            if not record.account_asset_id:
                # Only set a default value, do not erase user inputs
                record._onchange_account_depreciation_id()

    account_depreciation_id = fields.Many2one(
        comodel_name='account.account',
        string='Depreciation Account',
        check_company=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card', 'off_balance')), ('deprecated', '=', False)]",
        help="Account used in the depreciation entries, to decrease the asset value."
    )
    account_depreciation_expense_id = fields.Many2one(
        comodel_name='account.account',
        string='Expense Account',
        check_company=True,
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card', 'off_balance')), ('deprecated', '=', False)]",
        help="Account used in the periodical entries, to record a part of the asset as expense.",
    )
    
    @api.depends("depreciation_line_ids","analytic_line_ids")
    def _compute_irr(self):
        for rec in self:
            if rec.depreciation_line_ids and rec.irr_analytic_account:
            # Better to use purchase date as the true start, not depreciation date
            # But adhering to your logic, we ensure we get the years correctly:
                dates = rec.depreciation_line_ids.mapped("line_date")
                start_year = min(dates).year
                end_year = max(dates).year
                
                # Initial Investment (Outflow)
                year_summed = [rec.purchase_value * -1]
                
                for current_year in range(start_year, end_year + 1):
                    filter_start_date = date(current_year, 1, 1)
                    filter_end_date = date(current_year, 12, 31)
                    
                    analytic_lines = self.env["account.analytic.line"].search([
                        ("date", ">=", filter_start_date),
                        ("date", "<=", filter_end_date),
                        ("auto_account_id", "=", rec.irr_analytic_account.id)])
                    
                    analytic_line_amounts = analytic_lines.mapped("amount")
                    current_sum = sum(analytic_line_amounts) if analytic_line_amounts else 0
                    year_summed.append(current_sum)

                # Calculate IRR
                _logger.info(f"{year_summed=} {sum(year_summed)=}")
                if sum(year_summed) > 0:
                    rec.irr = npf.irr(year_summed)
                    _logger.info(f"{npf.irr(year_summed)=}")
                else:
                    rec.irr = 0
            else:
                rec.irr = 0


    @api.depends("account_move_line_ids","irr_analytic_account")
    def _compute_analytic_line_ids(self):
        for rec in self:
            if rec.account_move_line_ids:
                analytic_line_ids = self.env["account.analytic.line"].search(['|',("move_line_id", "in", rec.account_move_line_ids.ids),('auto_account_id', 'in', rec.irr_analytic_account.ids)])
                rec.analytic_line_ids = analytic_line_ids
            else:
                rec.analytic_line_ids = False

    @api.depends("analytic_line_ids")
    def _compute_analytic_line_count(self):
        for rec in self:
            if rec.account_move_line_ids:
                rec.analytic_line_count = len(rec.analytic_line_ids)
            else:
                rec.analytic_line_count = 0

    @api.depends("account_move_line_ids")
    def _compute_account_move_count(self):
        for rec in self:
            if rec.account_move_line_ids:
                rec.account_move_count = len(rec.account_move_line_ids.mapped("move_id").ids)
            else:
                rec.account_move_count = 0

    @api.onchange('account_depreciation_id')
    def _onchange_account_depreciation_id(self):
        if not self.original_move_line_ids:
            if not self.account_asset_id and self.state != 'model':
                # Only set a default value since it is visible in the form
                self.account_asset_id = self.account_depreciation_id

    def _get_own_book_value(self, date=None):
        self.ensure_one()
        return (self._get_residual_value_at_date(date) if date else self.value_residual) + self.salvage_value

    def _get_residual_value_at_date(self, date):
        """ Computes the theoretical value of the asset at a specific date.

            :param date: the date at which we want the asset's value
            :return: the value at date of the asset without taking reverse entries into account (as it should be in a "normal" flow of the asset)
        """
        current_and_previous_depreciation = self.depreciation_move_ids.filtered(
            lambda mv:
            mv.date < date
            and not mv.move_id.status_in_payment != "reversed"
        ).sorted('date', reverse=True)
        if not current_and_previous_depreciation:
            return 0

        if len(current_and_previous_depreciation) > 1:
            previous_value_residual = current_and_previous_depreciation[1].asset_remaining_value
        else:
            # If there is only one depreciation, we take the original depreciation value
            previous_value_residual = self.original_value - self.salvage_value - self.already_depreciated_amount_import

        # We compare the amount_residuals of the depreciations before and during the given date.
        # It applies the ratio of the period (to-given-date / total-days-of-the-period) to the amount of the depreciation.
        cur_depr_end_date = self._get_end_period_date(date)
        current_depreciation = current_and_previous_depreciation[0]
        cur_depr_beg_date = current_depreciation.asset_depreciation_beginning_date

        rate = self._get_delta_days(cur_depr_beg_date, date) / self._get_delta_days(cur_depr_beg_date, cur_depr_end_date)
        lost_value_at_date = (previous_value_residual - current_depreciation.asset_remaining_value) * rate
        residual_value_at_date = self.currency_id.round(previous_value_residual - lost_value_at_date)
        if self.currency_id.compare_amounts(self.original_value, 0) > 0:
            return max(residual_value_at_date, 0)
        else:
            return min(residual_value_at_date, 0)


    def action_asset_change(self):
        """ Returns an action opening the asset modification wizard.
        """
        self.ensure_one()
        new_wizard = self.env['asset.change'].create({
            'asset_id': self.id,
            'modify_action': 'resume' if self.env.context.get('resume_after_pause') else 'dispose',
            'analytic_distribution': self.analytic_distribution
        })
        return {
            'name': _('Change Asset'),
            'view_mode': 'form',
            'res_model': 'asset.change',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': new_wizard.id,
            'context': self.env.context,
        }
    
    def action_match_moves(self):
        """Bind existing journal entries to this asset's unbound lines.

        Server action: runs directly on the selected assets, no wizard.  Every
        stub line on the asset without a ``move_id`` — both the ``create``
        (acquisition) line and the ``depreciate`` lines — is scored against
        the candidate entries in the ledger, and the best pairs are bound.

        The matching rules live in :meth:`_match_find_pairs`; the binding is
        done through the same write path as the change-entry wizard, so the
        amount check and the ``asset_id`` sync on the entry's lines apply.

        Returns a notification with the result, which is what a server action
        from the list view should show.
        """
        total_bound = 0
        total_unmatched = 0
        details = []

        for asset in self:
            pairs, unmatched = asset._match_find_pairs()
            bound = asset._match_apply_pairs(pairs)
            total_bound += bound
            total_unmatched += unmatched
            if pairs or unmatched:
                details.append(_(
                    '%(asset)s: %(bound)s bound, %(left)s unmatched',
                    asset=asset.display_name,
                    bound=bound,
                    left=unmatched))

        if not details:
            raise UserError(_(
                'Nothing to match: every depreciation line of the selected '
                'asset(s) is already bound to an entry.'))

        message = '\n'.join(details)
        _logger.info(
            'asset_match: bound %s line(s) across %s asset(s) by %s',
            total_bound, len(self), self.env.user.login)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Match entries'),
                'message': message,
                'type': 'success' if total_bound else 'warning',
                'sticky': bool(total_unmatched),
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    @api.model
    def _match_is_throwaway_asset(self, asset):
        """Return True when *asset* looks like an auto-created artefact.

        OCA's ``account.move.action_post()`` creates an asset for every move
        line whose account carries an ``asset_profile_id``.  So posting a
        manual acquisition entry silently produces a second asset next to the
        one the accountant is working on.

        Such an asset has exactly one depreciation line (``create``), that
        line is bound to the entry, and the asset is still in draft — nobody
        has worked on it.
        """
        if not asset or asset.state != 'draft':
            return False
        lines = asset.depreciation_line_ids
        if len(lines) != 1:
            return False
        return lines.type == 'create' and bool(lines.move_id)

    def _match_find_pairs(self):
        """Return ``(pairs, unmatched_count)`` for this asset.

        ``pairs`` is a list of ``(score, asset_line, move)`` sorted by score.
        Only entries that pass the three gates (accounts, amount, date
        window) and are not already bound elsewhere are considered.
        """
        self.ensure_one()
        asset = self
        profile = asset.profile_id
        currency = asset.currency_id

        depr_account = profile.account_depreciation_id
        exp_account = profile.account_expense_depreciation_id
        if not (depr_account and exp_account):
            _logger.warning(
                'asset_match: asset %s has no depreciation/expense account, '
                'skipped', asset.id)
            return [], 0

        # Every stub line on the asset that has no entry yet.  That includes
        # the ``create`` line (the acquisition), which is matched against the
        # acquisition entry on the asset account.
        lines = asset.depreciation_line_ids.filtered(
            lambda al: al.type in ('create', 'depreciate') and not al.move_id)
        if not lines:
            return [], 0

        # Candidate entries touch any of the three accounts the board uses:
        # the asset account (acquisition), the depreciation account and the
        # depreciation expense account.
        asset_account = asset.account_asset_id or profile.account_asset_id
        search_accounts = depr_account | exp_account
        if asset_account:
            search_accounts |= asset_account
        candidates = self.env['account.move'].search([
            ('company_id', '=', asset.company_id.id),
            ('line_ids.account_id', 'in', search_accounts.ids),
            ('state', 'in', ('draft', 'posted')),
        ])
        if not candidates:
            return [], len(lines)

        # An entry already bound to a line of *another* asset is not a
        # candidate — it belongs there.
        #
        # Exception: OCA's ``action_post()`` auto-creates an asset when a move
        # line is booked on an account that has an ``asset_profile_id``.  A
        # manually booked acquisition entry therefore often owns a throw-away
        # asset whose only line is the ``create`` line pointing at the entry.
        # Such an asset is an artefact of the posting, not a real asset — the
        # entry is still a valid candidate for *this* asset.  We detect it by
        # the asset having exactly one line, of type ``create``, and no
        # journal entries of its own beyond the one we are looking at.
        taken = set()
        for bound_line in self.env['account.asset.line'].search([
            ('move_id', '!=', False),
            ('asset_id', '!=', asset.id),
        ]):
            owner = bound_line.asset_id
            if self._match_is_throwaway_asset(owner):
                continue
            taken.add(bound_line.move_id.id)
        candidates = candidates.filtered(lambda m: m.id not in taken)

        window = MATCH_DATE_WINDOW_DAYS
        pairs = []
        for line in lines:
            for move in candidates:
                score = asset._match_score(
                    line, move, depr_account, exp_account, currency, window)
                if score >= MATCH_MIN_SCORE:
                    pairs.append((score, line, move))
        pairs.sort(key=lambda p: p[0], reverse=True)

        # Greedy assignment: best score wins, one line and one entry each.
        used_lines, used_moves, chosen = set(), set(), []
        for score, line, move in pairs:
            if line.id in used_lines or move.id in used_moves:
                continue
            used_lines.add(line.id)
            used_moves.add(move.id)
            chosen.append((score, line, move))

        return chosen, len(lines) - len(chosen)

    @api.model
    def _match_score(self, line, move, depr_account, exp_account, currency,
                     window):
        """Score a (line, entry) pair.  Returns 0 when a gate fails.

        Gates (a failure means the entry cannot be this line's depreciation
        entry):

        For a ``create`` line (the acquisition) the gates differ: the entry
        must carry the asset account on the debit side and the amount must
        equal the line's amount.  There is no expense leg.

        For a ``depreciate`` line:

        * both depreciation accounts present on the entry,
        * the expense leg equals the line amount,
        * the entry date is within *window* days of the line date.

        Score: date proximity (40) + reference match (15).
        """
        accounts = move.line_ids.mapped('account_id')

        if line.type == 'create':
            asset_account = line.asset_id.account_asset_id \
                or line.asset_id.profile_id.account_asset_id
            if not asset_account or asset_account not in accounts:
                return 0
            asset_lines = move.line_ids.filtered(
                lambda aml: aml.account_id == asset_account)
            entry_amount = (sum(asset_lines.mapped('debit'))
                            - sum(asset_lines.mapped('credit')))
            if currency.compare_amounts(
                    abs(entry_amount), abs(line.amount)) != 0:
                return 0
        else:
            if depr_account not in accounts or exp_account not in accounts:
                return 0
            exp_lines = move.line_ids.filtered(
                lambda aml: aml.account_id == exp_account)
            entry_amount = (sum(exp_lines.mapped('debit'))
                            - sum(exp_lines.mapped('credit')))
            if currency.compare_amounts(
                    abs(entry_amount), abs(line.amount)) != 0:
                return 0

        delta = abs((move.date - line.line_date).days)
        if delta > window:
            return 0

        score = 40 if delta == 0 else int(40 * (1 - delta / window))

        ref = (move.ref or '').strip().lower()
        if ref:
            names = [n for n in (line.asset_id.name, line.name) if n]
            if any(n.lower() in ref for n in names):
                score += 15

        return score

    def _match_apply_pairs(self, pairs):
        """Bind *pairs* and return how many succeeded."""
        self.ensure_one()
        applied = 0
        throwaway = self.env['account.asset']
        for score, line, move in pairs:
            if line.move_id:
                continue
            try:
                with self.env.cr.savepoint():
                    line.with_context(
                        allow_asset_line_update=True,
                    ).write({'move_id': move.id})
                    # Keep the entry's own asset links in step.  For an
                    # acquisition entry that is the asset account; for a
                    # depreciation entry it is the two depreciation legs.
                    profile = self.profile_id
                    if line.type == 'create':
                        target_accounts = (self.account_asset_id
                                           or profile.account_asset_id)
                    else:
                        target_accounts = (profile.account_depreciation_id
                                           | profile.account_expense_depreciation_id)
                    legs = move.line_ids.filtered(
                        lambda aml: aml.account_id in target_accounts)
                    if legs:
                        # Remember the throw-away assets these lines belonged
                        # to, so they can be cleaned up afterwards.
                        throwaway |= legs.asset_id.filtered(
                            lambda a: a.id != self.id
                            and self._match_is_throwaway_asset(a))
                        legs.with_context(
                            allow_asset=True, allow_asset_removal=True,
                        ).write({'asset_id': self.id})

                    # The auto-created asset still holds its own ``create``
                    # line pointing at this entry.  Release it, otherwise the
                    # entry is bound twice and the ghost cannot be removed.
                    for ghost in throwaway:
                        ghost_lines = ghost.depreciation_line_ids.filtered(
                            lambda al: al.move_id == move)
                        if ghost_lines:
                            ghost_lines.with_context(
                                allow_asset_line_update=True,
                                unlink_from_asset=True,
                            ).write({'move_id': False})
                applied += 1
            except Exception:  # noqa: BLE001 - report, keep going
                _logger.warning(
                    'asset_match: could not bind line %s to move %s',
                    line.id, move.id, exc_info=True)

        # OCA's ``account.asset.line.unlink()`` refuses to delete a ``create``
        # line ("Du kan inte ta bort en tillgångsrad av typen
        # Avskrivningsunderlag"), so the auto-created asset cannot be removed
        # from here.  We release its line (done above) and report the asset so
        # an accountant can archive it.
        orphans = throwaway.exists().filtered(
            lambda a: not a.depreciation_line_ids.filtered('move_id'))
        if orphans:
            _logger.info(
                'asset_match: %s auto-created asset(s) left with no bound '
                'lines: %s', len(orphans), orphans.mapped('display_name'))
            self.message_post(body=_(
                '%(count)s auto-created asset(s) were left over from posting '
                'the matched entries and now have no bound lines: '
                '%(names)s. They can be archived manually.',
                count=len(orphans),
                names=', '.join(orphans.mapped('display_name'))))

        if applied:
            self.message_post(body=_(
                '%(count)s depreciation line(s) were bound to existing '
                'entries by %(user)s.',
                count=applied,
                user=self.env.user.display_name))
        return applied

    def action_analytic_lines(self):
        list_view_id = self.env.ref("analytic.view_account_analytic_line_tree").id
        return {
            'name': _('Asset connected analytic lines'),
            'views': [(list_view_id, 'list'),(False,'form')],
            'res_model': 'account.analytic.line',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.analytic_line_ids.ids)],
            'target': 'current',
        }

    def resume_after_pause(self):
        """ Sets an asset in 'paused' state back to 'open'.
        A Depreciation line is created automatically to remove  from the
        depreciation amount the proportion of time spent
        in pause in the current period.
        """
        self.ensure_one()
        return self.with_context(resume_after_pause=True).action_asset_modify()

    def pause(self, pause_date, message=None):
        """ Sets an 'open' asset in 'paused' state, generating first a depreciation
        line corresponding to the ratio of time spent within the current depreciation
        period before putting the asset in pause. This line and all the previous
        unposted ones are then posted.
        """
        self.ensure_one()
        self._create_move_before_date(pause_date)
        self.write({'state': 'paused'})
        self.message_post(body=_("Asset paused. %s", message if message else ""))
