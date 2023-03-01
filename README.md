# odoo-account

Module | Description
--- | ---
account_admin_rights | This module adds full accounting rights to the admin account. Purpose is to reduce the time it takes for initial set up when selecting a chart of accounts.
account_analytic_default_all_move_lines | This one makes it so that the default analytic account rules are applied to entry lines as well, otherwise the default rules are only applied on the invoice lines.
account_analytic_line_project | This one seems weird, adds project to an account.analytic.lines which it already has. Then it adds so that a project can have a list of all account.analytic.line connected to it, which is new.
account_analytic_move_ids | Adds so that there can be several analytic.account connected to an account.move.line. Instead of the default just one.
account_analytic_name | Changes display_name for account.analytic.account to include the group_id.name
account_analytic_tag_responsability_project_no | Adds types on an analytic account tag, so that we can set two new fields on a journal line and  purchase/sale Order Line.This is done so that we can filter on Area of Responsibility and Project Number fields. Which are set on a move line and a sale order line if the tag has either set as a type.This module also adds the requirement for invoice lines with an account code between 3000-9999 to have both a project and Cost Center tag.Also all purchase/sale order lines have to have a project tag.
account_analytics_extra_criteria |  Adds more criteria for analytic default rules.
account_contact_selection | Remove Account Selection Limitation On Contacts.
account_exchange_difference_analytic_tag | Adds the analytic tags from the original invoice to the currency difference invoice.
account_exchange_difference_draft | Adds an option to have the currency difference invoice in draft instead of having it automatically posted. This however has issues since odoo gives an error when you later try to change it or post it. So it is kinda useless.
account_journal_card_type | Adds new journal type that is used for card transactions.
account_journal_entry_mail_alias | This module allows users to create entry type account moves when people send an mail to a mail alias connected to a journal of the type general.
account_journal_select_payable_receivable_account | This module allows us to add a payable and a receivable type account on a journal. This replaces the default behaviour of odoo when it does a search and uses the first payable and a receivable type account it can find when considering an account to use. Instead it will first look at the account set on the journal.
account_journal_selection | Unlocks which accounts can be used on a journal.
account_move_disable_create | This module disables all ways of creating new records when in the account.move form view.
account_move_line_communication_payment_order |
account_move_line_group_by |
account_move_report_vat |
account_move_tier_validation_control |
account_move_tier_validation_implement |
account_payment_order_date |
account_payment_order_filter |
account_payment_order_filter_currency |
account_payment_order_regulatory_reporting |
account_payment_order_sepa_seb |
account_period |
account_period_contract |
account_reconciliation_override |
bank_payment_order_customization |
currency_exchange_rate |
odoo_invoice_analysis |
payment_order_file_name |
tier_all_validations_required |

