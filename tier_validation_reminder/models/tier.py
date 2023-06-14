from odoo import models, fields, api, _

class ReviewTier(models.Model):
    _inherit = "tier.review"

    def _review_reminder(self):
        tier_review_ids = self.env[self._name].search([("status", "=", "pending"),("resource_type", "=", "account.move")])
        template = self.env.ref('tier_validation_reminder.pending_tier_review_email_template')
        for review in tier_review_ids:
            if review.todo_by and review.reviewer_ids:
                review_user_id = review.reviewer_ids.filtered(
                    lambda review_user: review_user.name == review.todo_by
                )
                todo_data = {
                    'todo_by_email': review_user_id.email,
                    'todo_by_name': review_user_id.name
                }
                if len(review.next_review) > 1:
                    next_name = review.next_review.partition(' ')[2]
                    if review.name == next_name:
                        self.env['mail.template'].browse(template.id).with_context(todo_data).send_mail(review.id)

    def get_base_url(self):
        self.ensure_one()
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')


