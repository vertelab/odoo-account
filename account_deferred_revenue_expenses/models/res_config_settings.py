# Copyright 2026 Vertel AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    deferred_booking_method = fields.Selection(
        related='company_id.deferred_booking_method',
        readonly=False,
        string="Deferred Booking Model",
        help="How prepaid costs (periodiserade kostnader) are booked in this company.\n\n"
             "Model A (A_explicit_prepaid): the accountant codes the invoice line directly "
             "on the interim/periodiseringskonto (e.g. 1710/1790). The module only schedules "
             "the recurring releases to the expense account; no automatic rebook happens.\n\n"
             "Model B (B_auto_defer): the bill is coded normally on the expense/income account; "
             "when it is posted the module automatically parks the net amount on the interim "
             "(deferred) account and releases it to the expense account month by month via the "
             "daily posting job.\n\n"
             "VAT is NEVER deferred in either model: input VAT is booked directly and normally "
             "at posting. Only the net cost is parked and later released.",
    )
