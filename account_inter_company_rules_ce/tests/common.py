from odoo.tests import common
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestInterCompanyRulesCommon(AccountTestInvoicingCommon):
    """This test needs sale_purchase_inter_company_rules to run."""

    @classmethod
    def setUpClass(cls):
        super(TestInterCompanyRulesCommon, cls).setUpClass()

        cls.company_a = cls.company_data['company']
        cls.company_b = cls.setup_other_company()['company']

        cls.product_consultant = cls.env['product.product'].create({
            'name': 'Service',
            'uom_id': cls.env.ref('uom.product_uom_hour').id,
            'type': 'service',
            'taxes_id': [(6, 0, (cls.company_a.account_sale_tax_id + cls.company_b.account_sale_tax_id).ids)],
            'supplier_taxes_id': [(6, 0, (cls.company_a.account_purchase_tax_id + cls.company_b.account_purchase_tax_id).ids)],
            'company_id': False
        })

        cls.res_users_company_a = cls.env['res.users'].create({
            'name': 'User A',
            'login': 'usera',
            'email': 'usera@yourcompany.com',
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('account.group_account_user').id,
                cls.env.ref('account.group_account_manager').id
            ])]
        })

        cls.res_users_company_b = cls.env['res.users'].create({
            'name': 'User B',
            'login': 'userb',
            'email': 'userb@yourcompany.com',
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_b.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('account.group_account_user').id
            ])]
        })
