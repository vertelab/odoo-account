from odoo import models, fields, api, _

class AccountLoanTemplate(models.Model):
    _name = 'account.loan.template'
    _description = 'Account Loan Template'

    def _get_default_name(self, vals):
        return self.env["ir.sequence"].next_by_code("account.loan.template") or "/"

    def _default_company(self):
        return self.env.company

    def _account_by_code(self, code):
        return self.env['account.account'].search([('code', '=', code)], limit=1)

    @api.depends("journal_id", "company_id")
    def _compute_currency(self):
        for rec in self:
            rec.currency_id = rec.journal_id.currency_id or rec.company_id.currency_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self._get_default_name(vals)
        return super().create(vals_list)

    @api.depends("is_leasing")
    def _compute_journal_type(self):
        for record in self:
            if record.is_leasing:
                record.journal_type = "purchase"
            else:
                record.journal_type = "general"

    name = fields.Char(
        copy=False,
        required=True,
        default="/",
    )

    rate = fields.Float(
        required=True,
        default=0.0,
        digits=(8, 6),
        help="Currently applied rate",
        tracking=True,
    )

    start_date = fields.Date(
        help="Start of the moves",
        copy=False,
    )

    periods = fields.Integer(
        required=True,
        help="Number of periods that the loan will last",
    )

    method_period = fields.Integer(
        string="Period Length",
        default=1,
        help="State here the time between 2 depreciations, in months",
        required=True,
    )

    rate_type = fields.Selection(
        [("napr", "Nominal APR"), ("ear", "EAR"), ("real", "Real rate")],
        required=True,
        help="Method of computation of the applied rate",
        default="real",
    )
    loan_type = fields.Selection(
        [
            ("fixed-annuity", "Fixed Annuity"),
            ("fixed-annuity-begin", "Fixed Annuity Begin"),
            ("fixed-principal", "Fixed Principal"),
            ("interest", "Only interest"),
        ],
        required=True,
        help="Method of computation of the period annuity",
        default="fixed-annuity",
    )

    loan_amount = fields.Monetary(
        currency_field="currency_id",
        required=True,
    )
    residual_amount = fields.Monetary(
        currency_field="currency_id",
        default=0.0,
        required=True,
        help="Residual amount of the lease that must be payed on the end in "
             "order to acquire the asset",
    )
    round_on_end = fields.Boolean(
        help="When checked, the differences will be applied on the last period"
             ", if it is unchecked, the annuity will be recalculated on each "
             "period.",
    )
    payment_on_first_period = fields.Boolean(
        help="When checked, the first payment will be on start date",
    )
    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency",
        readonly=True,
    )
    journal_type = fields.Char(compute="_compute_journal_type")
    journal_id = fields.Many2one(
        "account.journal",
        domain="[('company_id', '=', company_id),('type', '=', journal_type)]",
        required=True,
    )
    short_term_loan_account_id = fields.Many2one(
        "account.account",
        domain="[('company_ids', '=', company_id)]",
        string="Short term account",
        help="Account that will contain the pending amount on short term",
        required=True,
        default=lambda self: self._account_by_code('2840')
    )
    long_term_loan_account_id = fields.Many2one(
        "account.account",
        string="Long term account",
        help="Account that will contain the pending amount on Long term",
        domain="[('company_ids', '=', company_id)]",
        default=lambda self: self._account_by_code('2390')
    )
    interest_expenses_account_id = fields.Many2one(
        "account.account",
        domain="[('company_ids', '=', company_id)]",
        string="Interests account",
        help="Account where the interests will be assigned to",
        required=True,
        default=lambda self: self._account_by_code('8410')
    )
    is_leasing = fields.Boolean(default=True)
    leased_asset_account_id = fields.Many2one(
        "account.account",
        domain="[('company_ids', '=', company_id)]",
        default=lambda self: self._account_by_code('5615')
    )
    product_id = fields.Many2one(
        "product.product",
        string="Loan product",
        help="Product where the amount of the loan will be assigned when the invoice is created",
        default=lambda self: self.env.ref('account_loan_template.product_product_loan')
    )
    interests_product_id = fields.Many2one(
        "product.product",
        string="Interest product",
        help="Product where the amount of interests will be assigned when the invoice is created",
        default=lambda self: self.env.ref('account_loan_template.product_product_interest')
    )

    post_invoice = fields.Boolean(
        default=True, help="Invoices will be posted automatically"
    )

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=_default_company,
    )
