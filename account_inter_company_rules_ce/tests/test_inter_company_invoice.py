from odoo import Command, tests
from .common import TestInterCompanyRulesCommon


@tests.tagged('post_install', '-at_install')
class TestInterCompanyInvoice(TestInterCompanyRulesCommon):

    @classmethod
    def setUpClass(cls):
        super(TestInterCompanyInvoice, cls).setUpClass()
        (cls.company_a + cls.company_b).write({
            'intercompany_generate_bills_refund': True,
        })
        cls.env.user.company_id = cls.company_b
        cls.env['account.chart.template'].try_loading('generic_coa', cls.company_b, install_demo=False)
        cls.env.user.company_id = cls.company_a
        cls.env['account.chart.template'].try_loading('generic_coa', cls.company_a, install_demo=False)

    def _configure_analytic(self, product=None, company=None, partner=None):
        display_name = "Inter Company"
        if company:
            self.env.user.company_id = company
            display_name = company.display_name
        analytic_plan = self.env['account.analytic.plan'].create({'name': f'Analytic Plan {display_name}'})
        analytic_account = self.env['account.analytic.account'].create({
            'name': f'Account {display_name}',
            'company_id': company and company.id,
            'plan_id': analytic_plan.id,
        })
        self.env['account.analytic.distribution.model'].create({
            'analytic_distribution': {analytic_account.id: 100},
            'product_id': product and product.id,
            'company_id': company and company.id,
            'partner_id': partner and partner.id,
        })
        return analytic_account

    def _create_post_invoice(self, product_id, analytic_distribution=None):
        invoice_line_vals = {
                'product_id': product_id,
                'price_unit': 100.0,
                'quantity': 1.0,
            }
        if analytic_distribution:
            invoice_line_vals['analytic_distribution'] = analytic_distribution

        customer_invoice = self.env['account.move'].with_user(self.res_users_company_a).create({
            'move_type': 'out_invoice',
            'partner_id': self.company_b.partner_id.id,
            'invoice_line_ids': [(0, 0, invoice_line_vals)]
        })
        customer_invoice.with_user(self.res_users_company_a).action_post()

    def test_00_inter_company_invoice_flow(self):
        self.env.ref('base.EUR').active = True
        self.res_users_company_a.company_ids = [(4, self.company_b.id)]
        customer_invoice = self.env['account.move'].with_user(self.res_users_company_a).create({
            'move_type': 'out_invoice',
            'partner_id': self.company_b.partner_id.id,
            'currency_id': self.env.ref('base.EUR').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_consultant.id,
                'price_unit': 450.0,
                'quantity': 1.0,
                'name': 'test'
            })]
        })
        self.assertEqual(customer_invoice.state, 'draft', 'Initially customer invoice should be in the "Draft" state')
        customer_invoice.with_user(self.res_users_company_a).action_post()
        self.assertEqual(customer_invoice.state, 'posted', 'Invoice should be in Open state.')
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)
        self.assertTrue(supplier_invoice.invoice_line_ids[0].quantity == 1, "Quantity in invoice line is incorrect.")
        self.assertTrue(supplier_invoice.invoice_line_ids[0].product_id.id == self.product_consultant.id, "Product in line is incorrect.")
        self.assertTrue(supplier_invoice.invoice_line_ids[0].price_unit == 450, "Unit Price in invoice line is incorrect.")
        self.assertTrue(supplier_invoice.invoice_line_ids[0].account_id.company_ids == self.company_b, "Applied account in created invoice line is not relevant to company.")
        self.assertTrue(supplier_invoice.state == "draft", "invoice should be in draft state.")
        self.assertEqual(supplier_invoice.amount_total, 517.5, "Total amount is incorrect.")
        self.assertTrue(supplier_invoice.company_id.id == self.company_b.id, "Applied company in created invoice is incorrect.")

    def test_default_analytic_distribution_company_b(self):
        analytic_account_company_b = self._configure_analytic(company=self.company_b, product=self.product_a)
        inter_company_analytic_account = self._configure_analytic(product=self.product_b)
        self._create_post_invoice(product_id=self.product_a.id, analytic_distribution={inter_company_analytic_account.id: 100})
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)
        self.assertEqual(supplier_invoice.invoice_line_ids.analytic_distribution, {str(analytic_account_company_b.id): 100, str(inter_company_analytic_account.id): 100})

    def test_no_default_analytic_distribution_company_b(self):
        inter_company_analytic_account = self._configure_analytic(product=self.product_b)
        self._create_post_invoice(product_id=self.product_a.id, analytic_distribution={inter_company_analytic_account.id: 100})
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)
        self.assertEqual(supplier_invoice.invoice_line_ids.analytic_distribution, {str(inter_company_analytic_account.id): 100})

    def test_multi_analytic_account_distribution_company_b(self):
        analytic_account_company_a = self._configure_analytic(company=self.company_a, product=self.product_a)
        inter_company_analytic_account = self._configure_analytic(product=self.product_a)
        self._create_post_invoice(product_id=self.product_a.id, analytic_distribution={
            analytic_account_company_a.id: 50,
            inter_company_analytic_account.id: 50,
            f"{analytic_account_company_a.id},{inter_company_analytic_account.id}": 100
        })
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)
        self.assertEqual(supplier_invoice.invoice_line_ids.analytic_distribution, {str(inter_company_analytic_account.id): 50})

    def test_default_analytic_distribution_company_a(self):
        analytic_account_company_a = self._configure_analytic(company=self.company_a, product=self.product_a)
        self._create_post_invoice(product_id=self.product_a.id, analytic_distribution={analytic_account_company_a.id: 100})
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)
        self.assertFalse(supplier_invoice.invoice_line_ids.analytic_distribution, "Analytic distribution should not be set on the invoice line.")

    def test_inter_company_invoice_flow_sub_companies(self):
        self.company_a.write({'child_ids': [
            Command.create({'name': 'Branch 1 of company a'}),
            Command.create({'name': 'Branch 2 of company a'}),
        ]})
        self.cr.precommit.run()
        branch_1, branch_2 = self.company_a.child_ids
        (branch_1 + branch_2).write({
            'intercompany_generate_bills_refund': True,
        })
        for branch in [branch_1, branch_2]:
            branch.intercompany_purchase_journal_id = self.env['account.journal'].create({
                'name': 'Purchases - Test',
                'code': 'TEXJ',
                'type': 'purchase',
                'company_id': branch.id,
            })
        self.env.user.write({
            'company_ids': [Command.set((branch_1 + branch_2).ids)],
            'company_id': branch_1.id,
        })
        customer_invoice = self.env['account.move'].with_context(allowed_company_ids=branch_1.ids).create({
            'move_type': 'out_invoice',
            'invoice_date': '2023-05-01',
            'partner_id': branch_2.partner_id.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'quantity': 1.0,
                'tax_ids': False,
            })]
        })
        customer_invoice.action_post()
        bill = self.env['account.move'].search([('move_type', '=', 'in_invoice')], limit=1)
        self.assertRecordValues(bill, [{
            'partner_id': branch_1.partner_id.id,
            'company_id': branch_2.id,
            'payment_reference': customer_invoice.payment_reference,
        }])

    def test_inter_company_invoice_product_not_accessible(self):
        self.product_a.company_id = self.company_a
        self._create_post_invoice(self.product_a.id)
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)
        self.assertFalse(supplier_invoice.invoice_line_ids.product_id, "No product should be set")
        self.assertEqual(supplier_invoice.invoice_line_ids.name, self.product_a.name)

    def test_analytic_distribution_model_partner(self):
        inter_company_analytic_account = self._configure_analytic(product=self.product_b)
        analytic_account_company_b = self._configure_analytic(company=self.company_b, partner=self.company_a.partner_id)
        self._create_post_invoice(product_id=self.product_a.id, analytic_distribution={inter_company_analytic_account.id: 100})
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)
        expected_distribution = {
            str(inter_company_analytic_account.id): 100,
            str(analytic_account_company_b.id): 100
        }
        self.assertEqual(supplier_invoice.invoice_line_ids.analytic_distribution, expected_distribution)

    def test_inter_company_attachment_with_contact_as_partner(self):
        company_partner = self.env['res.partner'].create({
            'name': 'company partner',
            'parent_id': self.company_b.partner_id.id,
        })
        customer_invoice = self.env['account.move'].create({
            'company_id': self.company_a.id,
            'move_type': 'out_invoice',
            'invoice_date': '2023-05-01',
            'partner_id': company_partner.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'quantity': 1.0,
                'tax_ids': False,
            })]
        })
        customer_invoice.action_post()
        self.env['account.move.send.wizard'].with_context(active_model='account.move', active_ids=customer_invoice.id)._generate_and_send_invoices(customer_invoice)
        bill = self.env['account.move'].search([('move_type', '=', 'in_invoice'), ('company_id', '=', self.company_b.id)], limit=1)
        self.assertTrue(bill.attachment_ids)
