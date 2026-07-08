"""Fiscal Year Close Wizard."""

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class AccountFiscalyearClose(models.TransientModel):
    _name = "account.fiscalyear.close"
    _description = "Close Fiscal Year"

    sure = fields.Boolean(string="I understand the consequences", default=False)

    def data_save(self):
        """Close the selected fiscal year(s).

        Validates that ALL child periods are closed first.
        """
        active_ids = self.env.context.get("active_ids", [])
        if not active_ids:
            raise ValidationError(_("No fiscal years selected."))

        fiscalyears = self.env["account.fiscal.year"].browse(active_ids)

        for fy in fiscalyears:
            # Check all periods are closed
            open_periods = fy.period_ids.filtered(lambda p: p.state != "done")
            if open_periods:
                raise ValidationError(
                    _("Cannot close fiscal year '%(fy)s': %(count)d period(s) are still open:\n%(periods)s",
                      fy=fy.name,
                      count=len(open_periods),
                      periods="\n".join(f"  - {p.name}" for p in open_periods))
                )

            fy.state = "done"

        return {"type": "ir.actions.act_window_close"}
