# Copyright 2019 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, modules
import logging

_logger = logging.getLogger(__name__)


class Users(models.Model):
    _inherit = "res.users"

    @api.model
    def review_user_count(self):
        user_reviews = {}
        # ~ domain = [
        # ~ ("status", "=", "partial_pending"),
        # ~ ("can_review", "=", True),
        # ~ ("id", "in", self.env.user.review_ids.ids),
        # ~ ]
        domain = ['|', '&', '&',
                  ("status", "=", "pending"),
                  ("can_review", "=", True),
                  ("id", "in", self.env.user.review_ids.ids),
                  ("status", "=", "partial_approved"),
                  ("can_review", "=", True),
                  ("id", "in", self.env.user.review_ids.ids),
                  ("done_by_all", "not in", self.env.user.id)
                  ]
        review_groups = self.env["tier.review"].read_group(domain, ["model"], ["model"])
        for review_group in review_groups:
            model = review_group["model"]
            reviews = self.env["tier.review"].search(review_group.get("__domain"))
            if reviews:
                records = (
                    self.env[model]
                    .with_user(self.env.user)
                    .with_context(active_test=False)
                    .search([("id", "in", reviews.mapped("res_id"))])
                    .filtered(lambda x: not x.rejected and x.can_review)
                )
                if len(records):
                    record = self.env[model]
                    user_reviews[model] = {
                        "name": record._description,
                        "model": model,
                        "icon": modules.module.get_module_icon(record._original_module),
                        "pending_count": len(records),
                    }
        _logger.warning(f"{user_reviews=}")
        _logger.warning(f"user_reviews.values()= {user_reviews.values()}")
        return list(user_reviews.values())

    @api.model
    def get_reviews(self, data):
        review_obj = self.env["tier.review"].with_context(lang=self.env.user.lang)
        res = review_obj.search_read([("id", "in", data.get("res_ids"))])
        for r in res:
            # Get the translated status value.
            r["display_status"] = dict(
                review_obj.fields_get("status")["status"]["selection"]
            ).get(r.get("status"))
            # Convert to datetime timezone
            if r["reviewed_date"]:
                r["reviewed_date"] = fields.Datetime.context_timestamp(
                    self, r["reviewed_date"]
                )
            if r.get('reviewer_ids'):
                reviewer_ids = self.env['res.users'].browse(r.get('reviewer_ids'))
                r['reviewers'] = ', '.join(reviewer.name for reviewer in reviewer_ids)
            if r.get('done_by_all'):
                done_by_all = self.env['res.users'].browse(r.get('done_by_all'))
                r['doer'] = ', '.join(doer.name for doer in done_by_all)
        return res

# Copyright 2019 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

# ~ from odoo import api, fields, models, modules


# ~ class Users(models.Model):
# ~ _inherit = "res.users"

# ~ review_ids = fields.Many2many(string="Reviews", comodel_name="tier.review")

# ~ @api.model
# ~ def review_user_count(self):
# ~ user_reviews = {}
# ~ domain = [
# ~ ("status", "=", "pending"),
# ~ ("can_review", "=", True),
# ~ ("id", "in", self.env.user.review_ids.ids),
# ~ ]
# ~ review_groups = self.env["tier.review"].read_group(domain, ["model"], ["model"])
# ~ for review_group in review_groups:
# ~ model = review_group["model"]
# ~ reviews = self.env["tier.review"].search(review_group.get("__domain"))
# ~ if reviews:
# ~ records = (
# ~ self.env[model]
# ~ .with_user(self.env.user)
# ~ .with_context(active_test=False)
# ~ .search([("id", "in", reviews.mapped("res_id"))])
# ~ .filtered(lambda x: not x.rejected and x.can_review)
# ~ )
# ~ if len(records):
# ~ record = self.env[model]
# ~ user_reviews[model] = {
# ~ "name": record._description,
# ~ "model": model,
# ~ "icon": modules.module.get_module_icon(record._original_module),
# ~ "pending_count": len(records),
# ~ }
# ~ return list(user_reviews.values())

# ~ @api.model
# ~ def get_reviews(self, data):
# ~ review_obj = self.env["tier.review"].with_context(lang=self.env.user.lang)
# ~ res = review_obj.search_read([("id", "in", data.get("res_ids"))])
# ~ for r in res:
# ~ # Get the translated status value.
# ~ r["display_status"] = dict(
# ~ review_obj.fields_get("status")["status"]["selection"]
# ~ ).get(r.get("status"))
# ~ # Convert to datetime timezone
# ~ if r["reviewed_date"]:
# ~ r["reviewed_date"] = fields.Datetime.context_timestamp(
# ~ self, r["reviewed_date"]
# ~ )
# ~ return res
