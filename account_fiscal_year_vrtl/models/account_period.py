"""Account Period model — uses delegation inheritance from date.range."""

import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

_logger = logging.getLogger(__name__)


class AccountPeriod(models.Model):
    _name = "account.period"
    _inherits = {"date.range": "date_range_id"}
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Period"
    _order = "date_start"

    date_range_id = fields.Many2one(
        "date.range",
        string="Date Range",
        required=True,
        ondelete="cascade",
        auto_join=True,
    )
    date_stop = fields.Date(
        related="date_range_id.date_end",
        string="End of Period",
        store=True,
        readonly=False,
    )
    fiscalyear_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        required=True,
        index=True,
        ondelete="cascade",
    )
    state = fields.Selection(
        [("draft", "Open"), ("done", "Closed")],
        string="Status",
        readonly=True,
        default="draft",
        tracking=True,
    )
    closing_date = fields.Date(
        string="Closing Date",
        help="Date when this period should be automatically closed.",
    )
    account_period_journal_ids = fields.One2many(
        "account.period.journal",
        "period_id",
        string="Journals",
        copy=True,
    )

    _sql_constraints = [
        (
            "name_company_uniq",
            "UNIQUE(name, company_id)",
            "The period name must be unique per company!",
        ),
    ]

    @api.constrains("date_start", "date_stop", "fiscalyear_id")
    def _check_dates(self):
        """Validate period dates fit within fiscal year and don't overlap."""
        for period in self:
            if not period.fiscalyear_id:
                continue
            fy = period.fiscalyear_id
            if period.date_start and fy.date_from and period.date_start < fy.date_from:
                raise ValidationError(
                    _("Period '%(period)s' starts before fiscal year '%(fy)s'.",
                      period=period.name, fy=fy.name)
                )
            if period.date_stop and fy.date_to and period.date_stop > fy.date_to:
                raise ValidationError(
                    _("Period '%(period)s' ends after fiscal year '%(fy)s'.",
                      period=period.name, fy=fy.name)
                )

    @api.constrains("date_start", "date_stop")
    def _check_duration(self):
        """Validate date_stop >= date_start."""
        for period in self:
            if period.date_start and period.date_stop and period.date_stop < period.date_start:
                raise ValidationError(
                    _("Period '%s': end date must be after start date.", period.name)
                )

    @api.constrains("date_start", "date_stop", "company_id")
    def _check_no_overlap(self):
        """Validate periods within same company don't overlap."""
        for period in self:
            if not period.date_start or not period.date_stop:
                continue
            overlapping = self.search([
                ("id", "!=", period.id),
                ("company_id", "=", period.company_id.id),
                ("date_start", "<=", period.date_stop),
                ("date_stop", ">=", period.date_start),
            ])
            if overlapping:
                raise ValidationError(
                    _("Period '%(period)s' overlaps with '%(other)s'.",
                      period=period.name, other=overlapping[0].name)
                )

    def find(self, dt=None, context=None, company_id=None):
        """Find the period containing a given date.

        Args:
            dt: Date string or datetime object (default: today)
            context: Optional context dict (unused, kept for compat)
            company_id: Company to search in (default: current company)

        Returns:
            account.period record or empty recordset
        """
        if dt is None:
            dt = fields.Date.context_today(self)
        if isinstance(dt, datetime):
            dt = dt.strftime(DEFAULT_SERVER_DATE_FORMAT)
        if not company_id:
            company_id = self.env.company.id

        return self.search([
            ("company_id", "=", company_id),
            ("date_start", "<=", dt),
            ("date_stop", ">=", dt),
        ], limit=1)

    def date2period(self, date):
        """Resolve a date string to a period record."""
        if not date:
            return self.browse()
        return self.find(dt=date)

    def next(self, period, step=1):
        """Get the Nth period after a given period."""
        self.ensure_one()
        if not period or not period.date_stop:
            return self.browse()
        periods = self.search([
            ("date_start", ">", period.date_stop),
            ("company_id", "=", self.company_id.id),
        ], order="date_start", limit=step)
        return periods[-1] if len(periods) == step else self.browse()

    def prev(self):
        """Get the period before this one."""
        self.ensure_one()
        if not self.date_start:
            return self.browse()
        return self.search([
            ("date_stop", "<", self.date_start),
            ("company_id", "=", self.company_id.id),
        ], order="date_stop desc", limit=1)

    def build_ctx_periods(self, period_from_id, period_to_id):
        """Get range of periods between two periods (inclusive)."""
        if not period_from_id or not period_to_id:
            return self.browse()
        return self.search([
            ("date_start", ">=", period_from_id.date_start),
            ("date_stop", "<=", period_to_id.date_stop),
            ("company_id", "=", self.company_id.id),
        ], order="date_start")

    def get_period_ids(self, period_start, period_stop):
        """Get period IDs between two periods (inclusive). Used by l10n_se_bokslut."""
        if not period_start or not period_stop:
            return []
        periods = self.search([
            ("date_start", ">=", period_start.date_start),
            ("date_stop", "<=", period_stop.date_stop),
            ("company_id", "=", period_start.company_id.id),
        ], order="date_start")
        return periods.ids

    def get_next_periods(self, last_period, length=3):
        """Get the next N periods after a given period."""
        if not last_period:
            return self.browse()
        return self.search([
            ("date_start", ">", last_period.date_stop),
            ("company_id", "=", last_period.company_id.id),
        ], order="date_start", limit=length)

    def period2month(self, period, short=False):
        """Convert period to month name string."""
        if not period or not period.date_start:
            return ""
        dt = period.date_start
        if short:
            return dt.strftime("%b")
        return dt.strftime("%B %Y")

    def sum_period_single(self, account):
        """Sum account balance for this period. Used by l10n_se_bokslut.

        Returns the numeric balance (debit - credit) for the account
        within this period.

        Args:
            account: account.account record

        Returns:
            float: balance (debit - credit)
        """
        self.ensure_one()
        target_move = self.env.context.get("target_move", "posted")
        domain = [
            ("account_id", "=", account.id),
            ("date", ">=", self.date_start),
            ("date", "<=", self.date_stop),
            ("company_id", "=", self.company_id.id),
        ]
        if target_move == "posted":
            domain.append(("move_id.state", "=", "posted"))
        elif target_move != "all":
            domain.append(("move_id.state", "!=", "cancel"))

        result = self.env["account.move.line"].read_group(
            domain,
            ["debit", "credit"],
            [],
        )
        if result:
            debit = result[0].get("debit", 0.0)
            credit = result[0].get("credit", 0.0)
            return debit - credit
        return 0.0

    def action_draft(self):
        """Re-open a closed period."""
        for period in self:
            if period.fiscalyear_id and period.fiscalyear_id.state == "done":
                raise ValidationError(
                    _("Cannot re-open period '%s' because fiscal year '%s' is closed.",
                      period.name, period.fiscalyear_id.name)
                )
            period.state = "draft"
            period.account_period_journal_ids.action_draft()

    def write(self, vals):
        """Block company_id change if moves reference this period."""
        if "company_id" in vals:
            for period in self:
                moves = self.env["account.move"].search_count([
                    ("date", ">=", period.date_start),
                    ("date", "<=", period.date_stop),
                    ("company_id", "!=", vals.get("company_id")),
                ])
                if moves:
                    raise ValidationError(
                        _("Cannot change company of period '%s': %d moves reference it.",
                          period.name, moves)
                    )
        return super().write(vals)

    def _cron_close_account_period(self):
        """Server action: auto-close periods past their closing_date."""
        today = fields.Date.context_today(self)
        open_periods = self.search([
            ("state", "=", "draft"),
            ("closing_date", "<=", today),
        ])
        for period in open_periods:
            _logger.info("Auto-closing period: %s (closing_date: %s)", period.name, period.closing_date)
            period.state = "done"

    @api.model
    def _normalize_date(self, date):
        """Parse date from string if needed."""
        if isinstance(date, str):
            return datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        return date

    def _period_domain(self, date, journal_id=None):
        """Build search domain for periods containing a date."""
        domain = [
            ("date_start", "<=", date),
            ("date_stop", ">=", date),
        ]
        if journal_id:
            domain.append(("account_period_journal_ids.journal_id", "=", journal_id))
        return domain


class AccountPeriodJournal(models.Model):
    _name = "account.period.journal"
    _description = "Period Journal"

    period_id = fields.Many2one(
        "account.period",
        string="Period",
        required=True,
        ondelete="cascade",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        ondelete="cascade",
    )
    closing_date = fields.Date(string="Closing Date")
    state = fields.Selection(
        [("draft", "Open"), ("done", "Closed")],
        string="Status",
        default="draft",
    )

    def action_draft(self):
        """Re-open closed journal periods."""
        self.state = "draft"
