"""Account Fiscal Year model."""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountFiscalYear(models.Model):
    _name = "account.fiscal.year"
    _description = "Fiscal Year"
    _order = "date_from, id"
    _rec_name = "name"

    name = fields.Char(string="Name", required=True)
    date_from = fields.Date(
        string="Start Date",
        required=True,
        default=lambda self: fields.Date.from_string(
            fields.Date.context_today(self)
        ).replace(month=1, day=1),
    )
    date_to = fields.Date(
        string="End Date",
        required=True,
        default=lambda self: fields.Date.from_string(
            fields.Date.context_today(self)
        ).replace(month=12, day=31),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    period_ids = fields.One2many(
        "account.period",
        "fiscalyear_id",
        string="Periods",
    )
    state = fields.Selection(
        [("draft", "Open"), ("done", "Closed")],
        string="Status",
        readonly=True,
        default="draft",
        tracking=True,
    )

    _sql_constraints = [
        (
            "name_company_uniq",
            "UNIQUE(name, company_id)",
            "The fiscal year name must be unique per company!",
        ),
    ]

    @api.constrains("date_from", "date_to")
    def _check_duration(self):
        """Validate date_from <= date_to."""
        for fy in self:
            if fy.date_from and fy.date_to and fy.date_to < fy.date_from:
                raise ValidationError(
                    _("Fiscal year '%s': end date must be after start date.", fy.name)
                )

    @api.constrains("date_from", "date_to", "company_id")
    def _check_no_overlap(self):
        """Validate fiscal years within same company don't overlap."""
        for fy in self:
            if not fy.date_from or not fy.date_to:
                continue
            overlapping = self.search([
                ("id", "!=", fy.id),
                ("company_id", "=", fy.company_id.id),
                ("date_from", "<=", fy.date_to),
                ("date_to", ">=", fy.date_from),
            ])
            if overlapping:
                raise ValidationError(
                    _("Fiscal year '%(fy1)s' overlaps with '%(fy2)s'.",
                      fy1=fy.name, fy2=overlapping[0].name)
                )

    def find(self, dt=None, exception=True):
        """Find fiscal year containing a date.

        Args:
            dt: Date string (default: today)
            exception: If True, raise error when not found

        Returns:
            account.fiscal.year record
        """
        if dt is None:
            dt = fields.Date.context_today(self)
        fy = self.search([
            ("company_id", "=", self.env.company.id),
            ("date_from", "<=", dt),
            ("date_to", ">=", dt),
        ], limit=1)
        if not fy and exception:
            raise ValidationError(
                _("No fiscal year defined for date %s. Please create a fiscal year first.", dt)
            )
        return fy

    def finds(self, dt=None, exception=True):
        """Find all fiscal years for a date (usually one, but can be multiple)."""
        if dt is None:
            dt = fields.Date.context_today(self)
        fys = self.search([
            ("company_id", "=", self.env.company.id),
            ("date_from", "<=", dt),
            ("date_to", ">=", dt),
        ])
        if not fys and exception:
            raise ValidationError(
                _("No fiscal year defined for date %s.", dt)
            )
        return fys

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """Search by name or by date range."""
        if not args:
            args = []
        domain = args + ["|", ("name", operator, name)]
        recs = self.search(domain, limit=limit)
        return recs.name_get()

    def action_draft(self):
        """Re-open a closed fiscal year."""
        for fy in self:
            fy.state = "draft"
            fy.mapped("period_ids").write({"state": "draft"})

    def _set_state(self):
        """Set fiscal year state to 'done' if ALL child periods are 'done'."""
        for fy in self:
            if all(p.state == "done" for p in fy.period_ids):
                fy.state = "done"

    def create_period(self, interval=1):
        """Create periods for this fiscal year.

        Args:
            interval: Number of months per period (1 = monthly)
        """
        self.ensure_one()
        if interval <= 0:
            raise ValidationError(_("Period interval must be positive."))

        # Delete existing non-closed periods? Or check first?
        existing = self.period_ids.filtered(lambda p: p.state == "done")
        if existing:
            raise ValidationError(
                _("Fiscal year '%s' already has closed periods. Cannot recreate.", self.name)
            )

        # Create periods spanning the fiscal year
        current_date = self.date_from
        period_count = 0

        while current_date <= self.date_to:
            # Calculate period end
            month = current_date.month + interval - 1
            year = current_date.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            period_end = current_date.replace(year=year, month=month, day=last_day)

            # Don't exceed fiscal year end
            if period_end > self.date_to:
                period_end = self.date_to

            # Create date_range
            date_range = self.env["date.range"].create({
                "name": "M{}".format(current_date.strftime("%y%m")),
                "date_start": current_date,
                "date_end": period_end,
                "company_id": self.company_id.id,
            })

            # Create period via delegation
            self.env["account.period"].create({
                "date_range_id": date_range.id,
                "fiscalyear_id": self.id,
                "code": current_date.strftime("%y%m"),
            })

            period_count += 1

            # Move to next period
            if period_end >= self.date_to:
                break
            next_day = period_end.day
            next_month = period_end.month + 1
            next_year = period_end.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            last_day_next = calendar.monthrange(next_year, next_month)[1]
            current_date = period_end.replace(
                year=next_year, month=next_month,
                day=min(next_day, last_day_next)
            )

        _logger.info(
            "Created %d periods for fiscal year '%s' (%s → %s)",
            period_count, self.name, self.date_from, self.date_to,
        )
        return period_count

    def create_period1(self):
        """Create monthly periods (convenience method)."""
        return self.create_period(interval=1)

    def compute_fiscalyear_dates(self, current_date):
        """Get fiscal year dates for a given date.

        Centralized lookup — inspired by Enterprise's pattern on res.company.
        Searches manual fiscal year records first, falls back to calendar year.

        Args:
            current_date: Date to find fiscal year for

        Returns:
            dict with date_from, date_to keys
        """
        self.ensure_one()
        fy = self.env["account.fiscal.year"].search([
            ("company_id", "=", self.company_id.id),
            ("date_from", "<=", current_date),
            ("date_to", ">=", current_date),
        ], limit=1)
        if fy:
            return {"date_from": fy.date_from, "date_to": fy.date_to}

        # Fallback: use calendar year with fiscalyear_last_month/day from company
        company = self.company_id
        last_month = int(company.fiscalyear_last_month) if hasattr(company, "fiscalyear_last_month") and company.fiscalyear_last_month else 12
        last_day = company.fiscalyear_last_day if hasattr(company, "fiscalyear_last_day") and company.fiscalyear_last_day else 31

        from odoo.tools.misc import get_fiscal_year
        date_from, date_to = get_fiscal_year(current_date, day=last_day, month=last_month)
        return {"date_from": date_from, "date_to": date_to}
