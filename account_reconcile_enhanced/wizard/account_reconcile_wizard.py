# Copyright 2026 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""
Enhanced reconciliation wizard for OCA's account.manual.reconcile.wizard.

Adds:
- Multi-account transfer support
- Tax computation on write-off lines
- Edit mode for single-line write-off
- Allow partials toggle
- Lock date validation
- Reconcile model auto-complete suggestions
- Date/journal/reference fields
"""

from collections import defaultdict
from datetime import timedelta

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError
from odoo.tools import groupby as tools_groupby
from odoo.tools import SQL
from odoo.tools.misc import formatLang


class AccountReconcileWizard(models.TransientModel):
    """Enhanced reconciliation wizard for selected account.move.line records.
    Works alongside OCA's account.manual.reconcile.wizard, adding:
    - Transfer between different accounts
    - Tax-aware write-offs
    - Single-line edit mode
    """

    _name = "account.reconcile.wizard"
    _description = "Enhanced Account Reconciliation Wizard"
    _check_company_auto = True

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "move_line_ids" not in fields_list:
            return res
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        if active_model != "account.move.line" or not active_ids:
            raise UserError(_("This can only be used on journal items"))
        move_line_ids = self.env["account.move.line"].browse(active_ids)
        accounts = move_line_ids.account_id
        if len(accounts) > 2:
            raise UserError(
                _(
                    "You can only reconcile entries with up to two different "
                    "accounts: %s",
                    ", ".join(accounts.mapped("display_name")),
                )
            )
        # Shadow AML values for multi-account (exchange diff handling)
        shadowed_aml_values = None
        if len(accounts) == 2:
            shadowed_aml_values = {
                aml: {"account_id": move_line_ids[0].account_id}
                for aml in move_line_ids.filtered(
                    lambda line: line.account_id != move_line_ids[0].account_id
                )
            }
        move_line_ids._check_amls_exigibility_for_reconciliation(
            shadowed_aml_values=shadowed_aml_values
        )
        res["move_line_ids"] = [Command.set(move_line_ids.ids)]
        return res

    # ==== Fields ====
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        readonly=True,
        compute="_compute_company_id",
    )
    move_line_ids = fields.Many2many(
        comodel_name="account.move.line",
        string="Move Lines to Reconcile",
        required=True,
    )
    reco_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Reconcile Account",
        compute="_compute_reco_wizard_data",
    )
    amount = fields.Monetary(
        string="Amount in Company Currency",
        currency_field="company_currency_id",
        compute="_compute_reco_wizard_data",
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Company Currency",
        related="company_id.currency_id",
    )
    amount_currency = fields.Monetary(
        string="Amount",
        currency_field="reco_currency_id",
        compute="_compute_reco_wizard_data",
    )
    reco_currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency for Reconciliation",
        compute="_compute_reco_wizard_data",
    )
    edit_mode = fields.Boolean(compute="_compute_edit_mode")
    edit_mode_amount = fields.Monetary(
        currency_field="company_currency_id",
        compute="_compute_edit_mode_amount",
    )
    edit_mode_amount_currency = fields.Monetary(
        string="Edit Mode Amount",
        currency_field="edit_mode_reco_currency_id",
        compute="_compute_edit_mode_amount_currency",
        store=True,
        readonly=False,
    )
    edit_mode_reco_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_edit_mode_reco_currency",
    )
    allow_partials = fields.Boolean(
        string="Allow Partials",
        compute="_compute_allow_partials",
        store=True,
        readonly=False,
    )
    force_partials = fields.Boolean(compute="_compute_reco_wizard_data")
    display_allow_partials = fields.Boolean(
        compute="_compute_display_allow_partials"
    )
    date = fields.Date(
        string="Date",
        compute="_compute_date",
        store=True,
        readonly=False,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        check_company=True,
        domain="[('type', '=', 'general')]",
        compute="_compute_journal_id",
        store=True,
        readonly=False,
        required=True,
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account",
        check_company=True,
        domain="[('account_type', '!=', 'off_balance')]",
    )
    is_rec_pay_account = fields.Boolean(
        compute="_compute_is_rec_pay_account"
    )
    to_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner",
        check_company=True,
        compute="_compute_to_partner_id",
        store=True,
        readonly=False,
    )
    label = fields.Char(string="Label", default="Write-Off")
    tax_id = fields.Many2one(
        comodel_name="account.tax",
        string="Tax",
        default=False,
        check_company=True,
    )
    to_check = fields.Boolean(
        string="To Check",
        default=False,
        help="Check if you are not certain of all the information of "
        "the counterpart.",
    )
    is_write_off_required = fields.Boolean(
        string="Is a write-off move required to reconcile",
        compute="_compute_is_write_off_required",
    )
    is_transfer_required = fields.Boolean(
        string="Is an account transfer required",
        compute="_compute_reco_wizard_data",
    )
    transfer_warning_message = fields.Char(
        compute="_compute_reco_wizard_data",
    )
    transfer_from_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Account Transfer From",
        compute="_compute_reco_wizard_data",
    )
    lock_date_violated_warning_message = fields.Char(
        compute="_compute_lock_date_violated_warning_message",
    )
    reco_model_id = fields.Many2one(
        comodel_name="account.reconcile.model",
        string="Reconciliation Model",
        store=False,
        check_company=True,
    )
    reco_model_autocomplete_ids = fields.Many2many(
        comodel_name="account.reconcile.model",
        string="All Reconciliation Models",
        compute="_compute_reco_model_autocomplete_ids",
    )

    # ==== Compute methods ====
    @api.depends("move_line_ids.company_id")
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.move_line_ids[0].company_id

    @api.depends("move_line_ids")
    def _compute_edit_mode(self):
        for wizard in self:
            wizard.edit_mode = len(wizard.move_line_ids) == 1

    @api.depends("move_line_ids")
    def _compute_edit_mode_amount_currency(self):
        for wizard in self:
            if wizard.edit_mode:
                wizard.edit_mode_amount_currency = wizard.amount_currency
            else:
                wizard.edit_mode_amount_currency = 0.0

    @api.depends("edit_mode_amount_currency")
    def _compute_edit_mode_amount(self):
        for wizard in self:
            if wizard.edit_mode:
                single_line = wizard.move_line_ids
                rate = (
                    abs(single_line.amount_currency / single_line.balance)
                    if single_line.balance
                    else 0.0
                )
                wizard.edit_mode_amount = (
                    single_line.company_currency_id.round(
                        wizard.edit_mode_amount_currency / rate
                    )
                    if rate
                    else 0.0
                )
            else:
                wizard.edit_mode_amount = 0.0

    @api.depends("move_line_ids")
    def _compute_edit_mode_reco_currency(self):
        for wizard in self:
            if wizard.edit_mode:
                wizard.edit_mode_reco_currency_id = (
                    wizard.move_line_ids.currency_id
                )
            else:
                wizard.edit_mode_reco_currency_id = False

    @api.depends("force_partials")
    def _compute_allow_partials(self):
        for wizard in self:
            wizard.allow_partials = (
                wizard.display_allow_partials and wizard.force_partials
            )

    @api.depends("move_line_ids")
    def _compute_display_allow_partials(self):
        for wizard in self:
            has_debit = has_credit = False
            for aml in wizard.move_line_ids:
                if aml.balance > 0.0 or aml.amount_currency > 0.0:
                    has_debit = True
                elif aml.balance < 0.0 or aml.amount_currency < 0.0:
                    has_credit = True
                if has_debit and has_credit:
                    wizard.display_allow_partials = True
                    break
            else:
                wizard.display_allow_partials = False

    @api.depends("move_line_ids", "journal_id", "tax_id")
    def _compute_date(self):
        for wizard in self:
            highest_date = max(aml.date for aml in wizard.move_line_ids)
            temp_move = self.env["account.move"].new(
                {"journal_id": wizard.journal_id.id}
            )
            wizard.date = temp_move._get_accounting_date(
                highest_date, bool(wizard.tax_id)
            )

    @api.depends("company_id")
    def _compute_journal_id(self):
        for wizard in self:
            wizard.journal_id = self.env["account.journal"].search(
                [
                    *self.env[
                        "account.journal"
                    ]._check_company_domain(wizard.company_id),
                    ("type", "=", "general"),
                ],
                limit=1,
            )

    @api.depends("account_id")
    def _compute_is_rec_pay_account(self):
        for wizard in self:
            wizard.is_rec_pay_account = wizard.account_id.account_type in (
                "asset_receivable",
                "liability_payable",
            )

    @api.depends("is_rec_pay_account")
    def _compute_to_partner_id(self):
        for wizard in self:
            if wizard.is_rec_pay_account:
                partners = wizard.move_line_ids.partner_id
                wizard.to_partner_id = (
                    partners if len(partners) == 1 else None
                )
            else:
                wizard.to_partner_id = None

    @api.depends("amount", "amount_currency")
    def _compute_is_write_off_required(self):
        for wizard in self:
            wizard.is_write_off_required = not wizard.company_currency_id.is_zero(
                wizard.amount
            ) or (
                wizard.reco_currency_id
                and not wizard.reco_currency_id.is_zero(wizard.amount_currency)
            )

    @api.depends("move_line_ids")
    def _compute_reco_wizard_data(self):
        """Compute reconciliation wizard data: currency, accounts, transfer info,
        and write-off amounts.
        """

        def get_transfer_data(move_lines):
            amounts_per_account = defaultdict(float)
            for line in move_lines:
                amounts_per_account[line.account_id] += line.amount_residual
            if abs(amounts_per_account[accounts[0]]) < abs(
                amounts_per_account[accounts[1]]
            ):
                transfer_from = accounts[0]
                transfer_to = accounts[1]
            else:
                transfer_from = accounts[1]
                transfer_to = accounts[0]

            amls_to_transfer = amls.filtered(
                lambda aml: aml.account_id == transfer_from
            )
            transfer_foreign_curr = amls.currency_id - amls.company_currency_id
            if len(transfer_foreign_curr) == 1:
                transfer_currency = transfer_foreign_curr
                transfer_amount_currency = sum(
                    aml.amount_currency for aml in amls_to_transfer
                )
            else:
                transfer_currency = amls.company_currency_id
                transfer_amount_currency = sum(
                    aml.balance for aml in amls_to_transfer
                )

            if (
                transfer_amount_currency == 0.0
                and transfer_currency != amls.company_currency_id
            ):
                transfer_currency = amls.company_currency_id
                transfer_amount_currency = sum(
                    aml.balance for aml in amls_to_transfer
                )

            amount_formatted = formatLang(
                self.env,
                abs(transfer_amount_currency),
                currency_obj=transfer_currency,
            )
            transfer_warning_message = _(
                "An entry will transfer %(amount)s from %(from_account)s "
                "to %(to_account)s.",
                amount=amount_formatted,
                from_account=(
                    transfer_from.display_name
                    if transfer_amount_currency < 0
                    else transfer_to.display_name
                ),
                to_account=(
                    transfer_to.display_name
                    if transfer_amount_currency < 0
                    else transfer_from.display_name
                ),
            )
            return {
                "transfer_from_account_id": transfer_from,
                "reco_account_id": transfer_to,
                "transfer_warning_message": transfer_warning_message,
            }

        def get_reco_currency(amls, aml_values_map):
            company_currency = amls.company_currency_id
            foreign_currencies = amls.currency_id - company_currency
            if len(foreign_currencies) == 0:
                return company_currency
            elif len(foreign_currencies) == 1:
                return foreign_currencies
            else:
                lines_with_residuals = self.env["account.move.line"]
                for residual, residual_values in aml_values_map.items():
                    if (
                        residual_values["amount_residual"]
                        or residual_values["amount_residual_currency"]
                    ):
                        lines_with_residuals += residual
                        if (
                            lines_with_residuals
                            and len(
                                lines_with_residuals.currency_id
                                - company_currency
                            )
                            > 1
                        ):
                            return False
                return (
                    lines_with_residuals.currency_id - company_currency
                ) or company_currency

        for wizard in self:
            amls = wizard.move_line_ids._origin
            accounts = amls.account_id

            wizard.reco_currency_id = False
            wizard.amount_currency = wizard.amount = 0.0
            wizard.force_partials = True
            wizard.transfer_from_account_id = False
            wizard.transfer_warning_message = False
            wizard.is_transfer_required = len(accounts) == 2

            if wizard.is_transfer_required:
                wizard.update(get_transfer_data(amls))
            else:
                wizard.reco_account_id = accounts

            shadowed_aml_values = {
                aml: {"account_id": wizard.reco_account_id} for aml in amls
            }
            aml_values_map = {
                aml: {
                    "aml": aml,
                    "amount_residual": aml.amount_residual,
                    "amount_residual_currency": aml.amount_residual_currency,
                }
                for aml in amls
            }

            reco_currency = get_reco_currency(amls, aml_values_map)
            if not reco_currency:
                continue

            residual_amounts = {
                aml: aml._prepare_move_line_residual_amounts(
                    aml_values,
                    reco_currency,
                    shadowed_aml_values=shadowed_aml_values,
                )
                for aml, aml_values in aml_values_map.items()
            }

            if all(
                reco_currency in rv
                for rv in residual_amounts.values()
                if rv
            ):
                wizard.reco_currency_id = reco_currency
            elif all(
                amls.company_currency_id in rv
                for rv in residual_amounts.values()
                if rv
            ):
                wizard.reco_currency_id = amls.company_currency_id
                reco_currency = wizard.reco_currency_id
            else:
                continue

            # Compute amounts
            most_recent_line = max(amls, key=lambda aml: aml.date)
            if not most_recent_line.amount_currency:
                rate = 0.0
            elif most_recent_line.currency_id == reco_currency:
                rate = abs(
                    most_recent_line.balance
                    / most_recent_line.amount_currency
                )
            else:
                rate = self.env["res.currency"]._get_conversion_rate(
                    reco_currency,
                    amls.company_currency_id,
                    amls.company_id,
                    most_recent_line.date,
                )

            wizard.amount_currency = sum(
                rv[wizard.reco_currency_id]["residual"]
                for rv in residual_amounts.values()
                if rv
            )
            amount_raw = sum(
                (
                    rv[amls.company_currency_id]["residual"]
                    if amls.company_currency_id in rv
                    else rv[wizard.reco_currency_id]["residual"] * rate
                )
                for rv in residual_amounts.values()
                if rv
            )
            wizard.amount = amls.company_currency_id.round(amount_raw)
            wizard.force_partials = False

    @api.depends("move_line_ids.move_id", "date")
    def _compute_lock_date_violated_warning_message(self):
        for wizard in self:
            date_after_lock = wizard._get_date_after_lock_date()
            lock_date_violated_warning_message = None
            if date_after_lock:
                lock_date_violated_warning_message = _(
                    "The date you set violates the lock date of one of "
                    "your entry. It will be overridden by the following "
                    "date: %(replacement_date)s",
                    replacement_date=date_after_lock,
                )
            wizard.lock_date_violated_warning_message = (
                lock_date_violated_warning_message
            )

    @api.depends("company_id", "move_line_ids.partner_id", "amount")
    def _compute_reco_model_autocomplete_ids(self):
        for wizard in self:
            domain = [
                ("company_id", "=", wizard.company_id.id),
                "|",
                ("match_partner_ids", "=", False),
                (
                    "match_partner_ids",
                    "any",
                    [("id", "in", wizard.move_line_ids.partner_id.ids)],
                ),
                "|",
                ("match_amount", "=", False),
                "|",
                "&",
                ("match_amount", "=", "lower"),
                ("match_amount_max", ">", wizard.amount),
                "|",
                "&",
                ("match_amount", "=", "greater"),
                ("match_amount_min", "<", wizard.amount),
                "&",
                ("match_amount", "=", "between"),
                "&",
                ("match_amount_min", "<", wizard.amount),
                ("match_amount_max", ">", wizard.amount),
            ]
            query = self.env["account.reconcile.model"].sudo()._search(
                domain
            )
            reco_model_ids = [
                r[0]
                for r in self.env.execute_query(
                    SQL(
                        """
                SELECT account_reconcile_model.id
                FROM %s
                JOIN account_reconcile_model_line line
                  ON line.model_id = account_reconcile_model.id
                WHERE %s
                GROUP BY account_reconcile_model.id
                HAVING COUNT(account_reconcile_model.id) = 1
            """,
                        query.from_clause,
                        query.where_clause or SQL("TRUE"),
                    )
                )
            ]
            wizard.reco_model_autocomplete_ids = self.env[
                "account.reconcile.model"
            ].browse(reco_model_ids)

    # ==== Onchange methods ====
    @api.onchange("reco_model_id")
    def _onchange_reco_model_id(self):
        if self.reco_model_id:
            self.label = self.reco_model_id.line_ids.label
            self.tax_id = (
                self.reco_model_id.line_ids.tax_ids[0]
                if self.reco_model_id.line_ids[0].tax_ids
                else None
            )
            self.account_id = self.reco_model_id.line_ids.account_id

    # ==== Constraints ====
    @api.constrains("edit_mode_amount_currency")
    def _check_min_max_edit_mode_amount_currency(self):
        for wizard in self:
            if wizard.edit_mode:
                if wizard.edit_mode_amount_currency == 0.0:
                    raise UserError(
                        _(
                            "The amount of the write-off of a single line "
                            "cannot be 0."
                        )
                    )
                is_debit = (
                    wizard.move_line_ids.balance > 0.0
                    or wizard.move_line_ids.amount_currency > 0.0
                )
                if (
                    is_debit
                    and wizard.edit_mode_amount_currency < 0.0
                ):
                    raise UserError(
                        _(
                            "The amount of the write-off of a single debit "
                            "line should be strictly positive."
                        )
                    )
                elif (
                    not is_debit
                    and wizard.edit_mode_amount_currency > 0.0
                ):
                    raise UserError(
                        _(
                            "The amount of the write-off of a single credit "
                            "line should be strictly negative."
                        )
                    )

    # ==== Business methods ====
    def _get_date_after_lock_date(self):
        self.ensure_one()
        lock_dates = self.company_id._get_violated_lock_dates(
            self.date, bool(self.tax_id), self.journal_id
        )
        if lock_dates:
            return lock_dates[-1][0] + timedelta(days=1)

    def _compute_write_off_taxes_data(self, partner):
        """Compute tax data for write-off lines."""
        AccountTax = self.env["account.tax"]
        amount_currency = (
            self.edit_mode_amount_currency or self.amount_currency
        )
        amount = self.edit_mode_amount or self.amount
        if not amount_currency:
            return None
        rate = abs(amount_currency / amount) if amount else 0.0
        tax_type = self.tax_id.type_tax_use if self.tax_id else None
        is_refund = (
            tax_type == "sale"
            and amount_currency > 0.0
        ) or (
            tax_type == "purchase" and amount_currency < 0.0
        )
        base_line = AccountTax._prepare_base_line_for_taxes_computation(
            self,
            partner_id=partner,
            currency_id=self.reco_currency_id,
            tax_ids=self.tax_id,
            price_unit=amount_currency,
            quantity=1.0,
            account_id=self.account_id,
            is_refund=is_refund,
            rate=rate,
            special_mode="total_included",
        )
        base_lines = [base_line]
        AccountTax._add_tax_details_in_base_lines(
            base_lines, self.company_id
        )
        AccountTax._round_base_lines_tax_details(
            base_lines, self.company_id
        )
        AccountTax._add_accounting_data_in_base_lines_tax_details(
            base_lines, self.company_id, include_caba_tags=True
        )
        tax_results = AccountTax._prepare_tax_lines(
            base_lines, self.company_id
        )
        _base_line, base_to_update = tax_results["base_lines_to_update"][0]
        tax_lines_data = []
        for tax_line_vals in tax_results["tax_lines_to_add"]:
            tax_lines_data.append(
                {
                    "tax_amount": tax_line_vals["balance"],
                    "tax_amount_currency": tax_line_vals["amount_currency"],
                    "tax_tag_ids": tax_line_vals["tax_tag_ids"],
                    "tax_account_id": tax_line_vals["account_id"],
                }
            )
        base_amount_currency = base_to_update["amount_currency"]
        base_amount = amount - sum(
            entry["tax_amount"] for entry in tax_lines_data
        )
        return {
            "base_amount": base_amount,
            "base_amount_currency": base_amount_currency,
            "base_tax_tag_ids": base_to_update["tax_tag_ids"],
            "tax_lines_data": tax_lines_data,
        }

    def _create_write_off_lines(self, partner=None):
        if not partner:
            partner = self.env["res.partner"]
        to_partner = (
            self.to_partner_id if self.is_rec_pay_account else partner
        )
        tax_data = (
            self._compute_write_off_taxes_data(to_partner)
            if self.tax_id
            else None
        )
        amount_currency = (
            self.edit_mode_amount_currency or self.amount_currency
        )
        amount = self.edit_mode_amount or self.amount
        line_ids_commands = [
            Command.create(
                {
                    "name": self.label or _("Write-Off"),
                    "account_id": self.reco_account_id.id,
                    "partner_id": partner.id,
                    "currency_id": self.reco_currency_id.id,
                    "amount_currency": -amount_currency,
                    "balance": -amount,
                }
            ),
            Command.create(
                {
                    "name": self.label,
                    "account_id": self.account_id.id,
                    "partner_id": to_partner.id,
                    "currency_id": self.reco_currency_id.id,
                    "tax_ids": self.tax_id.ids,
                    "tax_tag_ids": (
                        None
                        if not tax_data
                        else tax_data["base_tax_tag_ids"]
                    ),
                    "amount_currency": (
                        amount_currency
                        if not tax_data
                        else tax_data["base_amount_currency"]
                    ),
                    "balance": (
                        amount
                        if not tax_data
                        else tax_data["base_amount"]
                    ),
                }
            ),
        ]
        if tax_data:
            for tax_datum in tax_data["tax_lines_data"]:
                line_ids_commands.append(
                    Command.create(
                        {
                            "name": self.tax_id.name,
                            "account_id": tax_datum["tax_account_id"],
                            "partner_id": to_partner.id,
                            "currency_id": self.reco_currency_id.id,
                            "tax_tag_ids": tax_datum["tax_tag_ids"],
                            "amount_currency": tax_datum[
                                "tax_amount_currency"
                            ],
                            "balance": tax_datum["tax_amount"],
                        }
                    )
                )
        return line_ids_commands

    def create_write_off(self):
        """Create write-off move with the wizard data."""
        self.ensure_one()
        partners = self.move_line_ids.partner_id
        partner = partners if len(partners) == 1 else None
        write_off_vals = {
            "journal_id": self.journal_id.id,
            "company_id": self.company_id.id,
            "date": self._get_date_after_lock_date() or self.date,
            "checked": not self.to_check,
            "line_ids": self._create_write_off_lines(partner=partner),
        }
        write_off_move = self.env["account.move"].with_context(
            skip_invoice_sync=True,
            skip_invoice_line_sync=True,
        ).create(write_off_vals)
        write_off_move.action_post()
        return write_off_move

    def create_transfer(self):
        """Create transfer move between two accounts.
        Handles partner and currency grouping for correct partner ledger.
        """
        self.ensure_one()
        line_ids = []
        lines_to_transfer = self.move_line_ids.filtered(
            lambda line: line.account_id == self.transfer_from_account_id
        )
        other_lines = self.move_line_ids.filtered(
            lambda line: line.account_id == self.reco_account_id
        )

        default_destination_data = {}
        amounts_by_partner = defaultdict(
            lambda: defaultdict(lambda: defaultdict(float))
        )
        destination_data = defaultdict(lambda: defaultdict(float))

        for (partner, currency), lines_grp in tools_groupby(
            lines_to_transfer,
            lambda l: (l.partner_id, l.currency_id),
        ):
            amount = sum(line.amount_residual for line in lines_grp)
            amount_currency = sum(
                line.amount_residual_currency for line in lines_grp
            )
            line_ids += [
                Command.create(
                    {
                        "name": _(
                            "Transfer to %s",
                            self.reco_account_id.display_name,
                        ),
                        "account_id": self.transfer_from_account_id.id,
                        "partner_id": partner.id,
                        "currency_id": currency.id,
                        "amount_currency": -amount_currency,
                        "balance": -amount,
                    }
                ),
            ]
            sign = -1 if amount < 0 else 1
            default_destination_data[partner, currency, sign] = {
                "balance": amount,
                "amount_currency": amount_currency,
            }

        for (partner, currency), lines_grp in tools_groupby(
            other_lines,
            lambda l: (l.partner_id, l.currency_id),
        ):
            amount = -sum(line.amount_residual for line in lines_grp)
            amount_currency = -sum(
                line.amount_residual_currency for line in lines_grp
            )
            sign = -1 if amount < 0 else 1
            if (partner, currency, sign) in default_destination_data:
                default_amount = default_destination_data[
                    partner, currency, sign
                ]["balance"]
                default_amount_currency = default_destination_data[
                    partner, currency, sign
                ]["amount_currency"]
                amount_to_transfer = (
                    min(abs(amount), abs(default_amount)) * sign
                )
                amount_currency_to_transfer = (
                    min(
                        abs(amount_currency), abs(default_amount_currency)
                    )
                    * sign
                )
                destination_data[partner, currency, sign] = {
                    "balance": amount_to_transfer,
                    "amount_currency": amount_currency_to_transfer,
                }
                default_amount -= amount_to_transfer
                default_amount_currency -= amount_currency_to_transfer
                amount -= amount_to_transfer
                amount_currency -= amount_currency_to_transfer
                if not currency.is_zero(abs(default_amount)):
                    default_destination_data[partner, currency, sign] = {
                        "balance": default_amount,
                        "amount_currency": default_amount_currency,
                    }
                else:
                    del default_destination_data[partner, currency, sign]
            if not currency.is_zero(abs(amount)):
                amounts_by_partner[currency, sign][partner] = {
                    "balance": amount,
                    "amount_currency": amount_currency,
                }

        # Distribute remaining amounts
        for (partner, currency, sign) in list(
            default_destination_data.keys()
        ):
            amount = default_destination_data[partner, currency, sign][
                "balance"
            ]
            amount_currency = default_destination_data[
                partner, currency, sign
            ]["amount_currency"]
            for p in list(amounts_by_partner[currency, sign].keys()):
                if amount == 0:
                    break
                amount_to_transfer = (
                    min(
                        abs(amount),
                        abs(
                            amounts_by_partner[currency, sign][p][
                                "balance"
                            ]
                        ),
                    )
                    * sign
                )
                amount_currency_to_transfer = (
                    min(
                        abs(amount_currency),
                        abs(
                            amounts_by_partner[currency, sign][p][
                                "amount_currency"
                            ]
                        ),
                    )
                    * sign
                )
                amount -= amount_to_transfer
                amount_currency -= amount_currency_to_transfer
                destination_data[p, currency, sign][
                    "balance"
                ] += amount_to_transfer
                destination_data[p, currency, sign][
                    "amount_currency"
                ] += amount_currency_to_transfer
                amounts_by_partner[currency, sign][p][
                    "balance"
                ] -= amount_to_transfer
                amounts_by_partner[currency, sign][p][
                    "amount_currency"
                ] -= amount_currency_to_transfer
            if not currency.is_zero(abs(amount)):
                destination_data[partner, currency, sign][
                    "balance"
                ] += amount
                destination_data[partner, currency, sign][
                    "amount_currency"
                ] += amount_currency

        for (partner, currency, sign) in destination_data:
            line_ids += [
                Command.create(
                    {
                        "name": _(
                            "Transfer from %s",
                            self.transfer_from_account_id.display_name,
                        ),
                        "account_id": self.reco_account_id.id,
                        "partner_id": partner.id,
                        "currency_id": currency.id,
                        "amount_currency": destination_data[
                            partner, currency, sign
                        ]["amount_currency"],
                        "balance": destination_data[
                            partner, currency, sign
                        ]["balance"],
                    }
                ),
            ]

        transfer_vals = {
            "journal_id": self.journal_id.id,
            "company_id": self.company_id.id,
            "date": self._get_date_after_lock_date() or self.date,
            "line_ids": line_ids,
        }
        transfer_move = self.env["account.move"].create(transfer_vals)
        transfer_move.action_post()
        return transfer_move

    def reconcile(self):
        """Reconcile selected moves, with transfer and/or write-off if needed."""
        self.ensure_one()
        move_lines_to_reconcile = self.move_line_ids._origin
        do_transfer = self.is_transfer_required
        do_write_off = self.edit_mode or (
            self.is_write_off_required and not self.allow_partials
        )

        if do_transfer:
            transfer_move = self.create_transfer()
            lines_to_transfer = move_lines_to_reconcile.filtered(
                lambda line: line.account_id
                == self.transfer_from_account_id
            )
            transfer_line_from = transfer_move.line_ids.filtered(
                lambda line: line.account_id
                == self.transfer_from_account_id
            )
            transfer_line_to = transfer_move.line_ids.filtered(
                lambda line: line.account_id == self.reco_account_id
            )
            (lines_to_transfer + transfer_line_from).reconcile()
            move_lines_to_reconcile = (
                move_lines_to_reconcile
                - lines_to_transfer
                + transfer_line_to
            )

        if do_write_off:
            write_off_move = self.create_write_off()
            write_off_line_to_reconcile = write_off_move.line_ids[0]
            move_lines_to_reconcile += write_off_line_to_reconcile

        move_lines_to_reconcile.reconcile()
        return move_lines_to_reconcile

    def reconcile_open(self):
        """Reconcile and open the result in reconciliation view."""
        self.ensure_one()
        return self.reconcile().open_reconcile_view()



