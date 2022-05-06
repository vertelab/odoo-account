# Copyright 2019 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, modules


class Users(models.Model):
    _inherit = "res.users"

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
