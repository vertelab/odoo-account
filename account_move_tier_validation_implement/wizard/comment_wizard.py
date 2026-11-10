
from odoo import fields, models


class CommentWizard(models.TransientModel):
    _inherit = "comment.wizard"

    comment = fields.Char(required=False)

    def add_comment(self):
        self.ensure_one()
        rec = self.env[self.res_model].browse(self.res_id)
        self.review_ids.write({"comment": self.comment})
        if self.validate_reject == "validate":
            rec._validate_tier(self.review_ids)
        if self.validate_reject == "reject":
            rec._rejected_tier(self.review_ids)
        rec._update_counter()
