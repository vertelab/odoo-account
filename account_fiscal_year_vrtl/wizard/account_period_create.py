"""Period Create Wizard — create fiscal year + monthly periods in one step."""

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class AccountPeriodCreateWizard(models.TransientModel):
    _name = "account.period.create.wizard"
    _description = "Create Periods"

    fy_name = fields.Char(string="Fiscal Year Name", required=True)
    date_start = fields.Date(
        string="Start Date",
        required=True,
        default=lambda self: fields.Date.from_string(
            fields.Date.context_today(self)
        ).replace(month=1, day=1),
    )
    date_stop = fields.Date(
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

    def create_period1(self):
        """Create fiscal year + monthly periods."""
        return self._create_period(interval=1)

    def _create_period(self, interval=1):
        """Create fiscal year and generate periods."""
        self.ensure_one()

        if self.date_stop <= self.date_start:
            raise ValidationError(_("End date must be after start date."))

        # Check for overlapping fiscal years
        overlapping = self.env["account.fiscal.year"].search([
            ("company_id", "=", self.company_id.id),
            ("date_from", "<=", self.date_stop),
            ("date_to", ">=", self.date_start),
        ])
        if overlapping:
            raise ValidationError(
                _("Fiscal year '%(new)s' overlaps with existing '%(old)s'.",
                  new=self.fy_name, old=overlapping[0].name)
            )

        # Create fiscal year
        fy = self.env["account.fiscal.year"].create({
            "name": self.fy_name,
            "date_from": self.date_start,
            "date_to": self.date_stop,
            "company_id": self.company_id.id,
        })

        # Create periods
        fy.create_period(interval=interval)

        # Return action to view the fiscal year
        return {
            "type": "ir.actions.act_window",
            "name": _("Fiscal Year: %s", fy.name),
            "res_model": "account.fiscal.year",
            "res_id": fy.id,
            "view_mode": "form",
            "target": "current",
        }
