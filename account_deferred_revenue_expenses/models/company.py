# Copyright 2026 Vertel AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    deferred_booking_method = fields.Selection(
        [
            ('A_explicit_prepaid', 'A - Explicit prepaid'),
            ('B_auto_defer', 'B - Auto defer'),
        ],
        string='Deferred Booking Model',
        default='B_auto_defer',
        required=True,
        help="How prepaid costs (periodiserade kostnader) are booked in this company.\n\n"
             "Model A (explicit prepaid): the accountant codes the invoice line directly "
             "on the interim/periodiseringskonto (e.g. 1710/1790). The module only "
             "schedules the recurring releases from the interim account to the expense "
             "account. No automatic rebooking happens.\n\n"
             "Model B (auto defer): the bill is coded normally on the expense/income "
             "account; when it is posted, the module rebooks the deferred line onto the "
             "interim account so the net amount is parked there, and releases it to the "
             "expense account month by month via the daily posting job.\n\n"
             "In BOTH models VAT is never deferred: input VAT is booked directly and "
             "normally at posting. Only the net cost is parked and later released.",
    )
