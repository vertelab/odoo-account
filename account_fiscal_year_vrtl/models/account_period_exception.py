"""Period Lock Exception — grant temporary access to closed periods.

Inspired by OCA account_lock_to_date's exception pattern.
Only applies when close_period_hash_lock is False (soft period closing).
Hash-locked periods can never have exceptions.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountPeriodException(models.Model):
    _name = "account.period.exception"
    _description = "Period Lock Exception"
    _order = "create_date desc"

    period_id = fields.Many2one(
        "account.period",
        string="Period",
        required=True,
        ondelete="cascade",
        index=True,
        domain="[('state', '=', 'done')]",
    )
    company_id = fields.Many2one(
        related="period_id.company_id",
        store=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        help="User granted the exception. Leave empty to allow all users.",
    )
    end_datetime = fields.Datetime(
        string="Expires At",
        help="When the exception expires. Leave empty for permanent (until revoked).",
    )
    reason = fields.Text(
        string="Reason",
        required=True,
        help="Justification for this exception (e.g. auditor adjustment).",
    )
    state = fields.Selection([
        ("active", "Active"),
        ("expired", "Expired"),
        ("revoked", "Revoked"),
    ], string="Status", default="active", readonly=True, copy=False)
    active = fields.Boolean(
        compute="_compute_active",
        store=True,
    )
    create_uid = fields.Many2one(
        "res.users",
        string="Created By",
        readonly=True,
    )
    revoke_uid = fields.Many2one(
        "res.users",
        string="Revoked By",
        readonly=True,
    )

    @api.depends("state", "end_datetime")
    def _compute_active(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.active = (
                rec.state == "active"
                and (not rec.end_datetime or rec.end_datetime > now)
            )

    @api.constrains("period_id")
    def _check_hash_lock(self):
        """Cannot create exceptions for hash-locked periods."""
        for rec in self:
            if rec.period_id.company_id.close_period_hash_lock:
                raise ValidationError(
                    _("Cannot create exceptions for hash-locked periods. "
                      "Period '%s' is cryptographically locked.", rec.period_id.name)
                )

    def action_revoke(self):
        """Revoke this exception."""
        self.ensure_one()
        self.write({
            "state": "revoked",
            "revoke_uid": self.env.user.id,
        })
        _logger.info(
            "Period exception revoked for period '%s' by user '%s': %s",
            self.period_id.name, self.env.user.name, self.reason,
        )

    @api.model
    def _get_user_period_exception(self, period):
        """Check if the current user has an active exception for this period.

        Args:
            period: account.period record

        Returns:
            account.period.exception record or False
        """
        if not period or period.state != "done":
            return False

        # Hash-locked periods cannot have exceptions
        if period.company_id.close_period_hash_lock:
            return False

        domain = [
            ("period_id", "=", period.id),
            ("active", "=", True),
            "|",
            ("user_id", "=", False),
            ("user_id", "=", self.env.user.id),
        ]
        return self.search(domain, limit=1)

    def _cron_expire_exceptions(self):
        """Server action: mark expired exceptions."""
        now = fields.Datetime.now()
        expired = self.search([
            ("state", "=", "active"),
            ("end_datetime", "<=", now),
        ])
        expired.write({"state": "expired"})
        if expired:
            _logger.info("Expired %d period exceptions", len(expired))
