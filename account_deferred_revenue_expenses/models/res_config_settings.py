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
             "Model A (A_visma_cost_entry): the bill is booked normally on the "
             "expense/income account; when it is posted the module parks the net amount "
             "on the interim/periodiseringskonto so the cost account\u0027s net effect is zero "
             "and releases it month by month via the daily posting job.\n\n"
             "Model B (B_fortnox_interim_entry): the bill is booked directly on the "
             "depreciation/periodiseringskonto (already parked) and released month by "
             "month via the daily posting job.\n\n"
             "VAT is NEVER deferred in either model: input VAT is booked directly and "
             "normally at posting. Only the net cost is parked and later released.",
    )
