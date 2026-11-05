# Copyright 2026 Vertel Sverige AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # A/B is the BOOKING STYLE the user enters when creating a periodisation.
    #   A (Visma-style cost entry): the bill is booked normally on the cost/expense
    #     account (e.g. 5010); at posting the module parks the net cost on the
    #     interim/periodiseringskonto so the net effect on the P&L account is zero.
    #   B (Fortnox-style interim entry): the bill is booked directly on the
    #     depreciation/interim/periodiseringskonto (e.g. 1710).
    # In BOTH styles the daily cron releases the parked amount to the P&L account
    # over the profile's periods (identical periodisation effect) and VAT is never
    # deferred.
    deferred_booking_method = fields.Selection(
        [
            ('A_visma_cost_entry', 'A - Visma-style (cost account entry)'),
            ('B_fortnox_interim_entry', 'B - Fortnox-style (interim entry)'),
        ],
        string='Deferred Booking Model',
        default='B_fortnox_interim_entry',
        required=True,
        help="How prepaid costs (periodiserade kostnader) are booked in this company.\n\n"
             "Model A (Visma-style, cost-account entry): the bill is booked normally "
             "on the expense/income account (t.ex. 5010, the account the user enters). "
             "When it is posted, the module parks the net cost on the depreciation/"
             "periodiseringskonto (t.ex. 1710) so the net effect on the cost account is "
             "zero at booking\u0027s moment; the daily cron then releases it to the cost "
             "account over the profile periods.\n\n"
             "Model B (Fortnox-style, interim entry): the bill is booked directly on "
             "the depreciation/periodiseringskonto (t.ex. 1710, the account the user "
             "enters), i.e. already parked; the daily cron releases it to the cost "
             "account over the profile periods.\n\n"
             "Periodisation effect is the same in both models. In BOTH models VAT is "
             "never deferred: input VAT is booked directly at posting; only the net "
             "prepaid cost is parked and later released.",
    )

    # T/11824 - where the periodisation stubs land inside each period.
    # Legacy (the OCA account_asset_management entries the SFA data came from)
    # booked every stub on the LAST day of the month. The module's own default
    # was date_start + N months, which keeps the day-of-month of the start date.
    # Both conventions coexist in the migrated data, so this is a switch rather
    # than a hard rule.
    deferred_stub_month_end = fields.Boolean(
        string='Stubs on the Last Day of the Period',
        default=True,
        help="Place each periodisation stub on the last day of its period "
             "(month/quarter/year) instead of on the same day-of-month as the "
             "start date.\n\n"
             "On by default: it matches how the migrated legacy entries were "
             "booked, and it is what most Swedish accounting systems do. "
             "Turn it off to keep the start date's day-of-month.",
    )
