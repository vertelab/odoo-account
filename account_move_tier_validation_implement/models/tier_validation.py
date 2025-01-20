# Copyright 2017-19 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from ast import literal_eval

from lxml import etree

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import ValidationError


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    def _validation_request_mail(self, reviewers):
        tier_review_ids = reviewers.sorted(key='sequence').filtered(lambda reviewer: reviewer.status == 'pending')
        if tier_review_ids:
            next_reviewer = tier_review_ids[0]
            next_reviewer_partner_id = next_reviewer.reviewer_id.partner_id

            rec_obj = self.env[next_reviewer.model].browse(next_reviewer.res_id)
            action_id = self.env.ref('account.action_move_out_invoice_type', raise_if_not_found=False)

            company = self.env.user.company_id
            template = self.env.ref('account_move_tier_validation_implement.validation_email_template')

            render_context = {"company": company, "partner": next_reviewer_partner_id, "model": rec_obj, "action_id": action_id}
            mail_body = template._render(render_context, engine='ir.qweb', minimal_qcontext=True)
            mail_body = self.env['mail.render.mixin']._replace_local_links(mail_body)
            mail = self.env['mail.mail'].sudo().create({
               'subject': _('Validation Requested'),
               'email_from': company.catchall_formatted or company.email_formatted,
               'author_id': self.env.user.partner_id.id,
               'email_to': next_reviewer_partner_id.email,
               'body_html': mail_body,
            })
            mail.send()

    def _notify_review_requested(self, tier_reviews):
        subscribe = "message_subscribe"
        post = "message_post"
        if hasattr(self, post) and hasattr(self, subscribe):
            for rec in self:
                users_to_notify = tier_reviews.filtered(
                    lambda r: r.definition_id.notify_on_create and r.res_id == rec.id
                ).mapped("reviewer_ids")
                # self._validation_request_mail(tier_reviews)
                # Subscribe reviewers and notify
                getattr(rec, subscribe)(
                    partner_ids=users_to_notify.mapped("partner_id").ids
                )
                getattr(rec, post)(
                    subtype_xmlid=self._get_requested_notification_subtype(),
                    body=rec._notify_requested_review_body(),
                )

    def _validate_tier(self, tiers=False):

        self.ensure_one()
        tier_reviews = tiers or self.review_ids
        user_reviews = tier_reviews.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        user_reviews.write(
            {
                "status": "approved",
                "done_by": self.env.user.id,
                "reviewed_date": fields.Datetime.now(),
            }
        )
        for review in user_reviews:
            rec = self.env[review.model].browse(review.res_id)
            rec._notify_accepted_reviews()
        # TODO: FIX Issue with sending email
        # self._validation_request_mail(self.review_ids)

