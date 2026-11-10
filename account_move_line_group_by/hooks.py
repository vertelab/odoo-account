from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """
    This post-init-hook will create a rk.document for existing properties.
    """
    env = api.Environment(cr, SUPERUSER_ID, dict())
    models = ['property.property']

    env['account.move.line']._set_on_analytic_group_use_in_filter_all_record()

