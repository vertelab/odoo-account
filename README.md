# odoo-account

Module | Description
--- | ---
account_admin_rights | This module adds full accounting rights to the admin account. Purpose is to reduce the time it takes for initial set up when selecting a chart of accounts.
account_analytic_default_all_move_lines | This one makes it so that the default analytic account rules are applied to entry lines as well, otherwise the default rules are only applied on the invoice lines.
account_analytic_line_project | This one seems weird, adds project to an account.analytic.lines which it already has. Then it adds so that a project can have a list of all account.analytic.line connected to it, which is new.
account_analytic_move_ids | Adds so that there can be several analytic.account connected to an account.move.line. Instead of the default just one.
account_analytic_name | Changes display_name for account.analytic.account to include the group_id.name
account_analytic_tag_responsability_project_no | Adds types on an analytic account tag, so that we can set two new fields on a journal line and  purchase/sale Order Line.This is done so that we can filter on Area of Responsibility and Project Number fields. Which are set on a move line and a sale order line if the tag has either set as a type.This module also adds the requirement for invoice lines with an account code between 3000-9999 to have both a project and Cost Center tag. Also all purchase/sale order lines have to have a project tag.
account_analytics_extra_criteria |  Adds more criteria for analytic default rules.
account_contact_selection | Remove Account Selection Limitation On Contacts.
account_exchange_difference_analytic_tag | Adds the analytic tags from the original invoice to the currency difference invoice.
account_exchange_difference_draft | Adds an option to have the currency difference invoice in draft instead of having it automatically posted. This however has issues since odoo gives an error when you later try to change it or post it. So it is kinda useless.
account_journal_card_type | Adds new journal type that is used for card transactions.
account_journal_entry_mail_alias | This module allows users to create entry type account moves when people send an mail to a mail alias connected to a journal of the type general.
account_journal_select_payable_receivable_account | This module allows us to add a payable and a receivable type account on a journal. This replaces the default behaviour of odoo when it does a search and uses the first payable and a receivable type account it can find when considering an account to use. Instead it will first look at the account set on the journal.
account_journal_selection | Unlocks which accounts can be used on a journal.
account_move_disable_create | This module disables all ways of creating new records when in the account.move form view.
account_move_line_communication_payment_order | Overrides the method used to create an account.move.line so that the communication field gets filed with something atleast. This field is mandatory when creating payment.order.lines.
account_move_line_group_by | Module that gives us the capability to group account.move.lines  by account.analytic.group
account_move_report_vat | Adds vat number to sale pdf, also adds some page breaks to invoice pdf.
account_move_tier_validation_control | Adds two new fields on a res.user that we can use to control who and up to which amount a user can validate for account.move.
account_move_tier_validation_implement | Adds two new fields on an account.move that is used for setting up tier validation for account move.
account_payment_order_autogiro_lms | Swedish LMS training course on how paying a vendor bill behaves in Odoo 18 — the four payment paths (ordinary payment order, payment order with Autogiro, manual payment with a date, manual payment with Autogiro), what each one posts, and when a bank reconciliation is required. Training content only; the SFA-specific companion course lives in the se_sfa repo and auto-installs with this one.
account_payment_order_date | ??
account_payment_order_filter | TODO MOVE TO DIFFRENT REPO
account_payment_order_filter_currency | Adds a way to exclude some invoices from showing when making a payment order. Also adds a filter for currency when finding lines for the payment order. TODO split these two functions
account_payment_order_regulatory_reporting |When making bank files, with international payments in Sweden, we are sometimes required  to add Account Regulatory Reporting to the generated file.This is required, when the value of a payment is above 150 000 SEK.This module adds a List of most commonly used Regulatory Reporting codes, which can be found in the config menu for invoicing. When we make a payment.order and try to make bank payment lines then it will require the user to add Regulatory Reporting codes if the value is above 150 000 SEK and if the currency is not SEK, at which point this module will assume that it is an international payment.
account_payment_order_sepa_seb | Module that fixes some of the errors that the sepa files triggers for the SEB parser for Swedish payments.
account_period | Added period for accounting. Either 12 months or 4 quarters.
account_period_contract | When a contract generates an invoice this module makes sure that the account.period selected is for the date set on the invoice instead of the current date on the server.
account_reconciliation_override | Override OCA reconciliation module to allow reconcilation while in draft status
bank_payment_order_customization | This module changes the state of account.move to “In payment” after we have generated a file from an payment.order.
currency_exchange_rate | This module adds a field on an account.move that shows the rate for the currently selected currency.		
odoo_invoice_analysis | Adds product price in pivot invoice report. Also adds loc for the account.move tree view. TODO change repo?
payment_order_file_name | Sets name on the payment.order pdf.
tier_all_validations_required | This module makes it so that if you define a tier.definition that has multiple users that can validate. You can force it so that all of them have to validate instead of the default behaviour which is that just one of them needs to validate.

## Porteringsstatus — Odoo 20.0

Den här grenen är Odoo 20.0. Tabellen beskriver bara 20.0.

Genererad av `scripts/porting-status.py` — handredigera inte.

| Modul | Funktionsbeskrivning | Porteringsstatus |
|---|---|---|
| `account_3way_match_ai` | AI-driven 3-way matching of vendor bills against purchase orders. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `ai_agent_core` (odoo-ai; saknas i 20.0) |
| `account_3way_match_ce` | Adds 3-way matching on vendor bills for Community Edition. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `purchase` (finns inte i något addons-repo) |
| `account_accountant_ce` | Community accounting UI adjustments: "Accounting" naming and two form fields. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account_asset_management` (odooext-OCA-account-financial-tools; 20.0-grenen är tom) |
| `account_accountant_fleet_ce` | Adds fleet management to Community Edition accounting. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_fleet` (finns inte i något addons-repo) |
| `account_admin_rights` | Grants accounting access rights to the administrator user. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_ai` | OKF-kontraktet på account.move och account.account | ✓ `1.0` ✗ · 3 p-filer<br>⚠ `ai_agent_core` (odoo-ai; saknas i 20.0)<br>`account` (finns inte i något addons-repo) |
| `account_analytic_default_all_move_lines` | Account Analytic Move Default Rules. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `analytic` (finns inte i något addons-repo)<br>`account` (finns inte i något addons-repo) |
| `account_analytic_group` | Adds a group field to analytic accounts. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `analytic` (finns inte i något addons-repo)<br>`account` (finns inte i något addons-repo) |
| `account_analytic_line_project` | Adds a project field to analytic lines. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `analytic` (finns inte i något addons-repo)<br>`account` (finns inte i något addons-repo)<br>`project` (finns inte i något addons-repo) |
| `account_analytic_move_ids` | Account Analytic Move Ids. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `analytic` (finns inte i något addons-repo)<br>`account` (finns inte i något addons-repo) |
| `account_analytic_name` | Account Analytic Name. Change display_name. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `analytic` (finns inte i något addons-repo) |
| `account_analytic_replace` | Replaces analytic plans and accounts with automatic search redirection. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account` (finns inte i något addons-repo)<br>`analytic` (finns inte i något addons-repo) |
| `account_analytic_tag_responsability_project_no` | Adds types on a analytic account tag, so that we can set two new fields on a journal line. | ✓ `1.0` avstängd · 3 p-filer |
| `account_analytic_tier_validation` | Derive the invoice's reviewers from the analytic distribution (cost center) | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `analytic` (finns inte i något addons-repo)<br>`account` (finns inte i något addons-repo)<br>`base_tier_validation` (odooext-OCA-server-ux; 20.0-grenen är tom) |
| `account_analytics_extra_criteria` | Adds extra analytic criteria fields to journal items. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `analytic` (finns inte i något addons-repo)<br>`account` (finns inte i något addons-repo)<br>`hr` (finns inte i något addons-repo) |
| `account_asset_change` | Implement Asset changes . | ✓ `1.0` ✗ · 15 p-filer<br>⚠ `account_asset_management` (odooext-OCA-account-financial-tools; 20.0-grenen är tom) |
| `account_asset_lot_stock` | Create an asset connected to a Lot number. | ✓ `1.0` ✗ · 3 p-filer<br>⚠ `account` (finns inte i något addons-repo)<br>`account_asset_management` (odooext-OCA-account-financial-tools; 20.0-grenen är tom)<br>`stock` (finns inte i något addons-repo)<br>`sale` (finns inte i något addons-repo)<br>`purchase` (finns inte i något addons-repo) |
| `account_asset_lot_stock_personal_equipment` | Connect Created Asset to equipment. | ✓ `1.0` ✗ · 4 p-filer<br>⚠ `hr_personal_equipment_stock` (odoo-oca-hr; saknas i 20.0) |
| `account_asset_management_component` | Manage assets as components of a parent asset | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_asset_management` (odooext-OCA-account-financial-tools; 20.0-grenen är tom)<br>`project` (finns inte i något addons-repo) |
| `account_asset_management_grant` | Adds asset grants with their own depreciation handling. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_asset_management` (odooext-OCA-account-financial-tools; 20.0-grenen är tom) |
| `account_asset_management_report` | Depreciation board — pivot on asset lines, with department | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_asset_management` (odooext-OCA-account-financial-tools; 20.0-grenen är tom)<br>`hr` (finns inte i något addons-repo) |
| `account_attachment_directory` | Loads attachments from a directory and stores them on journal entries. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo) |
| `account_auto_reverse_vrtl` | Automatically reverse accounting entries on a specified date | ✓ `1.0` ✗ · 4 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_bill_approval` | Approve vendor bills with freely selectable approvers | ✓ `1.0` ✗ · 5 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_bill_approval_migration` | One-shot migration from purchase_vendor_bill_approval | ✓ `1.0` install · 1 p-fil |
| `account_budget_analytic_account` | MIS Builder for Analytic Account. | ✓ `1.0` ✗ · 12 p-filer<br>⚠ `account` (finns inte i något addons-repo)<br>`analytic` (finns inte i något addons-repo)<br>`base` (finns inte i något addons-repo)<br>`hr` (finns inte i något addons-repo) |
| `account_bulk_invoices` | Creates invoices in bulk through a wizard. | ✓ `1.0` ✗ · 3 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_chart_per_fiscalyear` | Chart of accounts versioned per fiscal year | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_chart_update` (odooext-OCA-account-financial-tools; 20.0-grenen är tom) |
| `account_closed` | Blocks posting into a closed accounting period. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo) |
| `account_commodity_demo` | Demo data for gold and silver commodity purchasing with 3-way matching. | ✓ `1.0` avstängd · 1 p-fil |
| `account_commodity_price` | Manages commodity prices, inventory revaluation and BOM integration. | ✓ `1.0` ✗ · 3 p-filer<br>⚠ `account` (finns inte i något addons-repo)<br>`stock` (finns inte i något addons-repo)<br>`stock_account` (finns inte i något addons-repo)<br>`mrp` (finns inte i något addons-repo) |
| `account_contact_selection` | Remove Account Selection Limitation On Contacts. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `contacts` (finns inte i något addons-repo)<br>`account` (finns inte i något addons-repo) |
| `account_customer_filter` | Adds a filter that only shows contacts with confirmed customer invoices. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo) |
| `account_deferred_revenue_expenses` | Handles deferred revenue and expenses with dedicated models. | ✓ `1.0` ✗ · 5 p-filer<br>⚠ `account` (finns inte i något addons-repo)<br>`analytic` (finns inte i något addons-repo) |
| `account_deferred_revenue_expenses_lms` | Swedish periodization training via website_slides | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `website_slides` (finns inte i något addons-repo) |
| `account_due_reminder` | Sends automatic payment reminders for overdue invoices. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo)<br>`contract_invoicingplan` (odoo-contract; saknas i 20.0)<br>`sms` (finns inte i något addons-repo) |
| `account_dynamic_reports` | Dynamic accounting reports for Odoo CE — balance sheet, P&L, general ledger, and more | ✓ `1.0` ✗ · 3 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_enablebanking` | Imports bank transactions through the Enable Banking API. | ✓ `1.0` ✗ · 6 p-filer<br>⚠ `account` (finns inte i något addons-repo)<br>`contacts` (finns inte i något addons-repo)<br>`base` (finns inte i något addons-repo)<br>`product` (finns inte i något addons-repo)<br>`mail` (finns inte i något addons-repo) |
| `account_exchange_difference_analytic_tag` | Adds the analytic tags from the orignal invoice on the currency differance invoice | ✓ `1.0` avstängd · 2 p-filer |
| `account_exchange_difference_draft` | Adds an option in settings to have the enchange differance invoice be set to draft | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_export_import_invoice` | Export a journal entry to XML and import it back | ✓ `1.0` ✗ · 5 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_financial_report_sorted` | Fixes sorting and UX for the Aged Partner Balance report. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_financial_report` (odooext-OCA-account-financial-reporting; 20.0-grenen är tom) |
| `account_fiscal_year_mis` | MIS Builder integration for fiscal year balance reporting | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_fiscal_year_closing` (finns inte i något addons-repo) |
| `account_fiscal_year_vrtl` | Fiscal years with monthly periods, period closing, and hash-locking | ✓ `1.0` ✗ · 4 p-filer<br>⚠ `account` (finns inte i något addons-repo)<br>`account_fiscal_year` (odooext-OCA-account-financial-tools; 20.0-grenen är tom)<br>`date_range` (odooext-OCA-server-ux; 20.0-grenen är tom) |
| `account_fortnox` | Syncs invoices and payments with Fortnox. | ✓ `1.0` ✗ · 4 p-filer<br>⚠ `crm` (finns inte i något addons-repo)<br>`l10n_se` (finns inte i något addons-repo)<br>`sale_management` (finns inte i något addons-repo) |
| `account_fortnox_delivery` | Glue module — sends the delivery method and delivery date to Fortnox | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `delivery` (finns inte i något addons-repo) |
| `account_fortnox_display_name` | Shows the Fortnox reference in the invoice display name. | ✓ `1.0` install · 2 p-filer |
| `account_import_excel` | Imports journal entries from Excel spreadsheets. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo) |
| `account_inexchange` | Fields for invoicing through Inexchange. | ✓ `1.0` avstängd · 2 p-filer |
| `account_inter_company_rules_ce` | Adds intercompany sale, purchase and invoice rules for Community Edition. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_invoice_ai` | Adds a mailbox for AI-assisted invoice handling. | ✓ `1.0` ✗ · 5 p-filer<br>⚠ `ai_agent` (odoo-ai; saknas i 20.0)<br>`account` (finns inte i något addons-repo)<br>`account_invoice_import` (odooext-OCA-edi; 20.0-grenen är tom)<br>`purchase` (finns inte i något addons-repo) |
| `account_invoice_ai_3way_match` | Bridge between AI invoice scanning and 3-way purchase matching | ✓ `1.0` install · 1 p-fil |
| `account_invoice_multi_currency` | Show the invoice totals in additional currencies | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo) |
| `account_invoice_scan_llm` | Scans invoices with an LLM and creates vendor bills. | ✓ `1.0` install · 1 p-fil |
| `account_journal_card_type` | Adds card types and card transactions to journals. | ✓ `1.0` ✗ · 7 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_journal_entry_mail_alias` | Show Mail Alias on Miscallenous | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account` (finns inte i något addons-repo)<br>`mail` (finns inte i något addons-repo) |
| `account_journal_select_payable_receivable_account` | Adds dedicated payable and receivable account fields on journals. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_journal_selection` | Removes the account selection limitation on contacts. | ✓ `1.0` ✗ · 3 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_journal_upload` | Added Journal Upload Button. | ✓ `1.0` avstängd · 1 p-fil |
| `account_loan_template` | Create loan templates that generate loan entries automatically. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_loan` (odooext-OCA-account-financial-tools; 20.0-grenen är tom)<br>`account_asset_management` (odooext-OCA-account-financial-tools; 20.0-grenen är tom) |
| `account_mass_invoice_generation` | Generates invoices in bulk for multiple partners. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_mis_budget` | Lets us generate budget based on the previous year. | ✓ `1.0` ✗ · 22 p-filer<br>⚠ `date_range` (odooext-OCA-server-ux; 20.0-grenen är tom)<br>`account` (finns inte i något addons-repo) |
| `account_mis_budget_forecast` | Replaces budgets with actuals and adds hierarchical budget forecasts. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `date_range` (odooext-OCA-server-ux; 20.0-grenen är tom)<br>`account` (finns inte i något addons-repo) |
| `account_mis_cash_flow_extended` | Cash flow forecast wizard — builds a forecast from the last three months of actuals | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo)<br>`mis_builder_cash_flow` (odooext-OCA-account-financial-reporting; 20.0-grenen är tom) |
| `account_mis_period_wizard` | Create the comparison periods (opening balance, period, closing balance) for a MIS report | ✓ `1.0` install · 1 p-fil |
| `account_mis_report_filter` | Adds filter options to MIS Builder reports. | ✓ `1.0` install · 2 p-filer |
| `account_move_contact` | Adds a contact field on invoices. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo)<br>`sale` (finns inte i något addons-repo) |
| `account_move_directory` | Loads journal entries from a directory into Odoo. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account` (finns inte i något addons-repo)<br>`edi_base` (odoo-edi; saknas i 20.0) |
| `account_move_disable_create` | Disable Creates on Account Move (Line) | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo)<br>`sale` (finns inte i något addons-repo)<br>`account_payment_partner` (odooext-OCA-bank-payment; 20.0-grenen är tom) |
| `account_move_line_communication_payment_order` | Sets payment. Lines communication field to the name of the account. Move as a last resort. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account_payment_order` (odooext-OCA-bank-payment; 20.0-grenen är tom) |
| `account_move_line_group_by` | Adds new options to groups journal lines by. | ✓ `1.0` avstängd · 1 p-fil |
| `account_move_red_narration` | Adds a second more visable narration field on the pdf. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_move_report` | Print Account Moves | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo) |
| `account_move_report_vat` | Adds Vat Number To the Invoice Report | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo)<br>`sale` (finns inte i något addons-repo) |
| `account_move_tier_validation_control` | Adds two new fields on a user. | ✓ `1.0` avstängd · 1 p-fil |
| `account_move_tier_validation_implement` | Adds a field on a account move to select validator. | ✓ `1.0` avstängd · 1 p-fil |
| `account_move_tier_validation_report` | Shows the bottlenecks in validation flow | ✓ `1.0` avstängd · 1 p-fil |
| `account_move_type_group` | Restrict journal entries per direction (in-bound vs out-bound) | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account` (finns inte i något addons-repo) |
| `account_notice_period` | Notice period text on payment terms, shown in the invoice footer | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo) |
| `account_payment_order_autogiro` | Handles Autogiro direct debit for vendor bills with a pending state. | ✓ `1.0` install · 2 p-filer |
| `account_payment_order_autogiro_lms` | Swedish training on the four vendor-bill payment paths in Odoo 18. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `website_slides` (finns inte i något addons-repo) |
| `account_payment_order_date` | Adds a new date preference that allows to set the date per row | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account_payment_order` (odooext-OCA-bank-payment; 20.0-grenen är tom) |
| `account_payment_order_filter` | Override prepare_payment_line_vals method so that the communication field gets set with something | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account_payment_order` (odooext-OCA-bank-payment; 20.0-grenen är tom) |
| `account_payment_order_filter_currency` | Adds the capability to filter payment order lines based on currency | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account_payment_order` (odooext-OCA-bank-payment; 20.0-grenen är tom) |
| `account_payment_order_hr` | Adds responsible user and manager to payment orders. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_payment_order_tier_validation` (odooext-OCA-bank-payment; 20.0-grenen är tom) |
| `account_payment_order_pending` | Keeps bills in an in-payment state until the bank reconciliation is done. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account_payment_order` (odooext-OCA-bank-payment; 20.0-grenen är tom) |
| `account_payment_order_regulatory_reporting` | Adds Account Regulatory Reporting for Sweden | ✓ `1.0` ✗ · 4 p-filer<br>⚠ `account_banking_pain_base` (odooext-OCA-bank-payment; 20.0-grenen är tom)<br>`account_payment_order` (odooext-OCA-bank-payment; 20.0-grenen är tom)<br>`account_banking_sepa_credit_transfer` (odooext-OCA-bank-payment; 20.0-grenen är tom)<br>`account_banking_sepa_direct_debit` (odooext-OCA-bank-payment; 20.0-grenen är tom) |
| `account_payment_order_sepa_seb` | Fixes SEPA payment file errors for SEB. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account_banking_pain_base` (odooext-OCA-bank-payment; 20.0-grenen är tom)<br>`account_banking_sepa_direct_debit` (odooext-OCA-bank-payment; 20.0-grenen är tom)<br>`account_payment_order` (odooext-OCA-bank-payment; 20.0-grenen är tom) |
| `account_payment_register_date` | Defaults the payment date to the invoice due date. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo) |
| `account_period_contract` | Manage Period based on Contract. | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account` (finns inte i något addons-repo)<br>`contract` (odooext-OCA-contract; 20.0-grenen är tom) |
| `account_period_vrtl` | Divides the fiscal year into 12 months or 4 quarters. | ✓ `1.0` avstängd · 8 p-filer |
| `account_period_vrtl_minimal` | Divides the fiscal year into 12 months or 4 quarters (minimal version). | ✓ `1.0` avstängd · 9 p-filer |
| `account_reconcile_currency_fix` | Fixes currency formatting in the OCA reconciliation widget. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_reconcile_oca` (odooext-OCA-account-reconcile; 20.0-grenen är tom) |
| `account_reconcile_enhanced` | Adds enhanced reconciliation tools to the OCA reconcile widget. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_reconcile_oca` (odooext-OCA-account-reconcile; 20.0-grenen är tom)<br>`account_reconcile_model_oca` (odooext-OCA-account-reconcile; 20.0-grenen är tom)<br>`account_reconcile_wizard` (odooext-OCA-account-reconcile; 20.0-grenen är tom) |
| `account_reconcile_oca_ux_fix` | Keeps the search filter in the reconcile tab after manual operation. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_reconcile_oca` (odooext-OCA-account-reconcile; 20.0-grenen är tom) |
| `account_reconciliation_override` | Override OCA reconciliation module to allow reconcilation while in draft status | ✓ `1.0` avstängd · 1 p-fil |
| `account_reconciliation_widget_journal` | Limit which journals and dates the reconcile widget may match against | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo)<br>`account_reconcile_oca` (odooext-OCA-account-reconcile; 20.0-grenen är tom) |
| `account_remove_unique_bank_account_constraint` | Remove unique bank account constraint on partner. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `base` (finns inte i något addons-repo) |
| `account_remove_unique_bank_number` | Relax Constraints on Unique Bank Number | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `base` (finns inte i något addons-repo) |
| `account_report_mis_import` | Convert MIS Builder reports to account.report (migration tool) | ✓ `1.0` avstängd · 1 p-fil |
| `accountant_hr_expense_ce` | Bridges accounting and expenses for Community Edition. | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `hr_expense` (finns inte i något addons-repo) |
| `bank_payment_order_customization` | Bank Payment Order Customization | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account_payment_order` (odooext-OCA-bank-payment; 20.0-grenen är tom) |
| `currency_exchange_rate` | Currency Exchange Rate | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo) |
| `odoo_invoice_analysis` | Show product price in pivot invoice report | ✓ `1.0` avstängd · 1 p-fil |
| `partner_statement_vrtl` | Consistent sign convention and remaining amount for partner statements | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `partner_statement` (odooext-OCA-account-financial-reporting; 20.0-grenen är tom)<br>`report_xlsx_helper` (odooext-OCA-reporting-engine; 20.0-grenen är tom) |
| `payment_order_file_name` | Override OCA reconciliation module to allow reconcilation while in draft status | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `account_payment_order` (odooext-OCA-bank-payment; 20.0-grenen är tom) |
| `project_tags_company` | Add company_id to project.tags | ✓ `1.0` ✗ · 2 p-filer<br>⚠ `project` (finns inte i något addons-repo) |
| `res_config_quests` | Add a quests field to res.config.settings | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `base_setup` (finns inte i något addons-repo) |
| `split_invoice_by_attachments` | Split an invoice with many attachments into copies with single files | ✓ `1.0` ✗ · 1 p-fil<br>⚠ `account` (finns inte i något addons-repo)<br>`mail` (finns inte i något addons-repo) |
| `tier_all_validations_required` | (ingen beskrivning i manifestet) | ✓ `1.0` avstängd · 1 p-fil |
| `tier_validation_reminder` | Sends reminder to the next person pending a tier review. | ✓ `1.0` avstängd · 2 p-filer |
