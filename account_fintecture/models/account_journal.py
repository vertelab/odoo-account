import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timezone, timedelta, date
from dateutil.relativedelta import relativedelta, MO, SU
import calendar
import re
import requests
from pprint import pprint
from re import search


_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    notify_user_id = fields.Many2one("res.users", string="User to Notify", help="User to notify when transaction sync fails")


    def action_sync_transactions_with_fintecture(self):
        return {
            'name': _('Fintecture Transaction'),
            'res_model': 'fintecture.transaction.wizard',
            'view_mode': 'form',
            'context': {
                'default_journal_id': self.id,
                'default_account_uuid': self.bank_account_id.account_uuid,
                'default_fintecture_customer_id': self.bank_account_id.fintecture_customer_id,
                'default_fintecture_account_id': self.bank_account_id.fintecture_account_id
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_sync_balances_with_fintecture(self):
        partner_id = self.bank_id.api_contact_integration
        api_url, private_key, application_id, base_headers = partner_id.request_essentials()
        account_uid = self.bank_account_id.account_uuid
        account_balance = requests.get(f"{api_url}/accounts/{account_uid}/balances", headers=base_headers)
        if account_balance.status_code == 200:
            _logger.info(f'Fintecture Balances {account_balance.json()}')
        else:
            _logger.error(f"Error response {account_balance.status_code}: {account_balance.text}", )
            return False

    def _valid_journals(self):
        journal_ids = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('bank_account_id', '!=', False),
            ('bank_account_id.account_uuid', '!=', False)
        ])
        return journal_ids

    def _compute_interval(self):
        interval_type = self.env['ir.config_parameter'].sudo().get_param('fintecture.interval_type')
        interval_number = self.env['ir.config_parameter'].sudo().get_param('fintecture.interval_number')

        date_from = date.today() - relativedelta(days=1)
        date_to = date.today() - relativedelta(days=1)
        current_date = date.today()

        if interval_type == 'minutes':
            date_from = date.today() - relativedelta(minutes=int(interval_number))
            date_to = date.today() - relativedelta(minutes=int(interval_number))

        if interval_type == 'hours':
            date_from = date.today() - relativedelta(hours=int(interval_number))
            date_to = date.today() - relativedelta(hours=int(interval_number))

        if interval_type == 'days':
            date_from = date.today() - relativedelta(days=int(interval_number))
            date_to = date.today() - relativedelta(days=int(interval_number))

        if interval_type == 'weeks':
            date_from = (current_date - relativedelta(weekday=MO, weeks=int(interval_number)))
            date_to = (date_from + relativedelta(weekday=SU, days=+6))

        if interval_type == 'months':
            date_from = current_date - relativedelta(day=1, months=int(interval_number))
            date_to = date_from + relativedelta(months=+1, days=-1)

        return date_from, date_to

    def _cron_sync_transactions(self):
        for journal in self._valid_journals():
            bank_statement_id = self.env['account.bank.statement'].search([('journal_id', '=', journal.id)])

            date_from, date_to = self._compute_interval()

            if not bank_statement_id:
                date_from = self._compute_starting_fiscal_year_date()
                date_to = date.today() - relativedelta(days=1)

            self.env['fintecture.transaction.wizard'].create({
                'journal_id': journal.id,
                'account_uuid': journal.bank_account_id.account_uuid,
                'date_from': date_from,
                'date_to': date_to,
            }).with_context({'_cron_task': True}).action_sync_transactions()

    def _compute_starting_fiscal_year_date(self):
        fiscalyear_last_month = self.env.user.company.fiscalyear_last_month
        fiscalyear_last_day = self.env.user.company.fiscalyear_last_day
        previous_year = datetime.today().year - 1
        starting_fiscal_year = date(
            previous_year, int(fiscalyear_last_month), fiscalyear_last_day
        ) + relativedelta(days=1)
        return starting_fiscal_year


class FintectureTransactions(models.TransientModel):
    _name = "fintecture.transaction.wizard"

    journal_id = fields.Many2one('account.journal', string="Journal")

    account_uuid = fields.Char(string="Account UUID")

    fintecture_customer_id = fields.Char(string="Fintecture Customer ID")

    fintecture_account_id = fields.Char(string="Fintecture Account ID")

    date_from = fields.Date(string="From", default=fields.Date.today)

    date_to = fields.Date(string="To", default=fields.Date.today)

    def _fetch_transactions(self):

        partner_id = self.journal_id.bank_id.api_contact_integration

        query = {
            "date_from": self.date_from,
            "date_to": self.date_to
        }

        transaction_responses = partner_id.get_account_transactions(self.fintecture_customer_id,self.fintecture_account_id,query)

        if transaction_responses.status_code != 200:

            _logger.error(transaction_responses.text)
            raise ValidationError("Failed to get transactions")
            

        return transaction_responses.json()


    def _schedule_activity(self, err_message):
        if self.journal_id.notify_user_id:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': 'Fintecture Failed',
                'user_id': self.journal_id.notify_user_id.id,
                'note': err_message,
                'res_model_id': self.env['ir.model'].search([('model', '=', 'account.journal')]).id,
                'res_id': self.journal_id.id,
            })

    def _sieve_out_existing_transactions(self, transactions):
        bank_statement_id = self.env['account.bank.statement.line']
        v_transactions = list(
            filter(
                lambda trans: not bank_statement_id.search([('payment_ref', '=', trans['attributes']['transaction_id'])]),
                transactions["data"])
        )
        return v_transactions

    def action_sync_transactions(self):

        date_name = f"{self.date_from} - {self.date_to}"
        statement_number = '01'
        transactions = self._sieve_out_existing_transactions(
            self.with_context(self.env.context)._fetch_transactions()
        )

        bank_statement_id = self.env['account.bank.statement'].search([
            ('journal_id', '=', self.journal_id.id)], order='id desc')
        bank_statement_id = bank_statement_id.filtered(lambda statement: search(date_name, statement.name))

        if bank_statement_id:
            statement_number = "{:02d}".format(int(bank_statement_id[0].name.split('/')[-1]) + 1)

        if transactions:
            bank_statement_id = self.env['account.bank.statement'].create({
                'journal_id': self.journal_id.id,
                'name': f"{date_name}/{statement_number}"
            })

        for transaction in transactions:
            
            transaction_id = transaction["id"]

            transaction = transaction["attributes"]

            partner_id = False

            bank_statement_line_id = self.env['account.bank.statement.line'].search([
                ('payment_ref', '=', transaction['transaction_id'])
            ])

            if not bank_statement_line_id:
                if transaction.get('counterparty'):

                    partner_id = self._sync_partner(transaction['counterparty']['name']).id
                
                else:

                    pass

                if transaction.get('credit_debit') == 'CREDIT':
                    amount = float(transaction['amount'])
                else:
                    amount = -float(transaction['amount'])

                currency_id = self.env['res.currency'].search([
                    ('name', '=', transaction['currency'])])
                if currency_id != self.journal_id.currency_id:
                    err_message = (f"The Bank Account {self.journal_id.bank_account_id.acc_number} has transaction "
                                   f"with a different currency ({currency_id.name}) to the journal "
                                   f"({self.journal_id.currency_id.name}). They need to be the same.")
                    self._schedule_activity(err_message)
                    raise UserError(_(err_message))

                self.env['account.bank.statement.line'].create({
                    'date': transaction.get('value_date'),
                    'invoice_date': transaction.get('booking_date'),
                    'amount': amount,
                    'narration': transaction.get('communication'),
                    'transaction_type': transaction.get('credit_debit'),
                    'ref': transaction_id,
                    'partner_id': partner_id,
                    'payment_ref': transaction.get('transaction_id'),
                    'statement_id': bank_statement_id.id,
                })

    def _sync_partner(self, partner_name):
        partner_name = re.sub(r'\s+', ' ', partner_name)
        partner_id = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if not partner_id:
            partner_id = self.env['res.partner'].create({
                'name': partner_name
            })
        return partner_id


class Fintecture(models.TransientModel):
    _name = "fintecture.wizard"
    _description = "Fintecture Wizard"
    _rec_name = 'code'

    bank_id = fields.Many2one("res.bank", string="Bank")
    code = fields.Char(string="Code")
    fintecture_customer_id = fields.Char(string="Fintecture Customer ID")
    session_id = fields.Char(string="Session ID")
    date_from = fields.Date(string="From", default=fields.Date.today)
    date_to = fields.Date(string="To", default=fields.Date.today)

    def sync_accounts(self):
        if not self.bank_id:
            raise ValidationError(_("Select a Bank!"))
        return_to_bank_accounts = self._create_session()
        return return_to_bank_accounts


    def _create_session(self):

        _logger.critical("create session")
        
        partner_id = self.bank_id.api_contact_integration

        accounts_response = partner_id.get_accounts(self.code,self.fintecture_customer_id)

        accounts = accounts_response.json()

        if accounts_response.status_code == 200:
           
            self._sync_bank_accounts(accounts)
           
            return {
            'name': _('Return To Bank Account'),
            'res_model': 'res.partner.bank',
            'view_mode': 'tree,form',
            'target': 'current',
            'type': 'ir.actions.act_window',
            }
        
        else:
            _logger.error(f"Error response {accounts_response.get('code')}: {accounts_response['errors'][0].get('message')}")
            raise ValidationError("failed to get bank accounts")


    def _sync_bank_accounts(self, accounts):

        valid_bank_accounts = list(map(lambda x: x, accounts["data"]))
        
        for account in valid_bank_accounts:
            
            fintecture_account_id = account["id"]

            account = account["attributes"]

            partner_bank_id = self.env['res.partner.bank'].search([
                ('acc_number', '=', account['iban'])
            ], limit=1)

            if partner_bank_id:
                partner_bank_id.write({
                    'acc_number': account['iban'],
                    'bank_id': self.bank_id.id,
                    'account_uuid': account['account_id'],
                    'fintecture_customer_id': self.fintecture_customer_id,
                    'fintecture_account_id': fintecture_account_id
                })
            
            else:
                partner_bank_id = self.env['res.partner.bank'].create({
                    'partner_id': self.env.company.id,
                    'acc_number': account['iban'],
                    'bank_id': self.bank_id.id,
                    'account_uuid': account['account_id'],
                    'fintecture_customer_id': self.fintecture_customer_id,
                    'fintecture_account_id': fintecture_account_id
                })


    def _sync_account_journal(self, account):
        journal_id = self.env['account.journal'].search([
            ('code', '=', account.acc_number[:5])
        ], limit=1)
        if not journal_id:
            self.env['account.journal'].create({
                'name': account.acc_number[:5],
                'code': account.acc_number[:5],
                'type': 'bank',
                'bank_account_id': account.id,
                'currency_id': account.currency_id.id
            })

    def _sync_partner(self, partner_name):
        partner_name = re.sub(r'\s+', ' ', partner_name)
        partner_id = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if not partner_id:
            partner_id = self.env['res.partner'].create({
                'name': partner_name
            })
        return partner_id
