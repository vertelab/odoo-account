import logging

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timezone, timedelta, date
from dateutil.relativedelta import relativedelta, MO, SU
import calendar
import re
import requests, json
from pprint import pprint
from re import search

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):

    _inherit = "account.journal"

    notify_user_id = fields.Many2one("res.users", string="User to Notify", help="User to notify when transaction sync "
                                                                                "fails")

    def action_sync_transactions_with_saltedge(self):
        return {
            'name': _('Saltedge Transaction'),
            'res_model': 'saltedge.transaction.wizard',
            'view_mode': 'form',
            'context': {
                'default_journal_id': self.id,
                'default_account_uuid': self.bank_account_id.account_uuid,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_sync_balances_with_saltedge(self):
        
        partner_id = self.bank_id.api_contact_integration

        balance_url = self.create_url(f"accounts?connection_id={partner_id.saltedge_connection_id}")

        headers = partner_id.create_headers("GET",balance_url)

        account_uid = self.bank_account_id.account_uuid

        accounts_response = requests.get(balance_url, headers=headers)
        
        if accounts_response.status_code == 200:

            json_response = accounts_response.json()["data"]

            balance = list(filter(lambda balance: balance["id"] == account_uid , json_response))

            if len(balance) == 0:

                raise ValidationError("Could not find the bank account on saltedge") 

            _logger.info(f'Saltedge Balances {balance[0]["balance"]}')
        
        else:

            _logger.error(f"Error response {accounts_response.status_code}: {accounts_response.text}", )

            raise ValidationError("failed to sync balance")
        

    def _valid_journals(self):
        journal_ids = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('bank_account_id', '!=', False),
            ('bank_account_id.account_uuid', '!=', False)
        ])
        return journal_ids

    def _compute_interval(self):
        interval_type = self.env['ir.config_parameter'].sudo().get_param('saltedge.interval_type')
        interval_number = self.env['ir.config_parameter'].sudo().get_param('saltedge.interval_number')

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

            self.env['saltedge.transaction.wizard'].create({
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



class SaltedgeTransactions(models.TransientModel):

    _name = "saltedge.transaction.wizard"

    journal_id = fields.Many2one('account.journal', string="Journal")

    account_uuid = fields.Char(string="Account UUID")

    date_from = fields.Date(string="From", default=fields.Date.today)

    date_to = fields.Date(string="To", default=fields.Date.today)


    def _fetch_transactions(self):

        partner_id = self.journal_id.bank_id.api_contact_integration

        transaction_url = partner_id.create_url(f"transactions?connection_id={partner_id.saltedge_connection_id}&account_id={self.account_uuid}")

        headers = partner_id.create_headers("GET",transaction_url)

        response = requests.get(headers=headers, url=transaction_url).json()

        _logger.error(response)

        response = response.get("data")

        return response        


    def _get_creditor(self, merchant_id):

        partner_id = self.journal_id.bank_id.api_contact_integration

        creditor_url = partner_id.create_url("merchants")

        payload = json.dumps({"data": [merchant_id]})

        headers = partner_id.create_headers("POST", creditor_url, payload=payload)

        response = requests.post(creditor_url,data=payload,headers=headers).json()

        _logger.error(response)

        response = response.get("data")

        if len(response) != 0:

            _logger.error(response)

            response = response[0].get("names")[0].get("value")

        return response


    def _schedule_activity(self, err_message):
        if self.journal_id.notify_user_id:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': 'Saltedge Failed',
                'user_id': self.journal_id.notify_user_id.id,
                'note': err_message,
                'res_model_id': self.env['ir.model'].search([('model', '=', 'account.journal')]).id,
                'res_id': self.journal_id.id,
            })


    def _sieve_out_existing_transactions(self, transactions):
        bank_statement_id = self.env['account.bank.statement.line']
        v_transactions = list(
            filter(
                lambda trans: not bank_statement_id.search([('payment_ref', '=', trans.get('id'))]),
                transactions)
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

            self._create_bank_statement(transaction)
     

    def _create_bank_statement(self, transaction):

        partner_id = False

        bank_statement_line_id = self.env['account.bank.statement.line'].search([
            ('payment_ref', '=', transaction.get('id'))
        ])

        if not bank_statement_line_id:
            
            if transaction.get('extra'):

                creditor = self._get_creditor(transaction.get('extra')["id"])

                if len(creditor) != 0:

                    partner_id = self._sync_partner(creditor).id

            amount = float(transaction.get('amount'))

            currency_id = self.env['res.currency'].search([
                ('name', '=', transaction.get('currency_code'))])
            if currency_id != self.journal_id.currency_id:
                err_message = (f"The Bank Account {self.journal_id.bank_account_id.acc_number} has transaction "
                                f"with a different currency ({currency_id.name}) to the journal "
                                f"({self.journal_id.currency_id.name}). They need to be the same.")
                self._schedule_activity(err_message)
                raise UserError(_(err_message))

            self.env['account.bank.statement.line'].create({
                'date': transaction.get('made_on'),
                'invoice_date': transaction.get('posting_date'),
                'amount': amount,
                'narration': transaction.get('description'),
                'transaction_type': "DBIT" if float(transaction.get('amount')) < 0 else "CRDT",
                'ref': transaction.get('extra')["id"],
                'partner_id': partner_id,
                'payment_ref': transaction.get('extra')["id"],
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


class Saltedge(models.TransientModel):
    _name = "saltedge.wizard"
    _description = "Saltedge Wizard"
    _rec_name = 'code'

    bank_id = fields.Many2one("res.bank", string="Bank")
    code = fields.Char(string="Code")
    session_id = fields.Char(string="Session ID")
    date_from = fields.Date(string="From", default=fields.Date.today)
    date_to = fields.Date(string="To", default=fields.Date.today)


    def sync_accounts(self):

        if not self.bank_id:
            raise ValidationError(_("Select a Bank!"))
        auth_data = self._create_session()
        return auth_data


    def get_account_ids(self):

        partner_id = self.bank_id.api_contact_integration

        account_response = partner_id.get_account()

        account_ids = []

        for account in account_response:

            _logger.error(account)

            if account.get("extra"):
            
                if account.get("extra").get("iban"):

                    _logger.error(f"account={account}")

                    account_id = account

                    account_ids.append(account_id)
        
        _logger.error(account_ids)

        return account_ids


    def _create_session(self):

        _logger.critical("create session")
       
        partner_id = self.bank_id.api_contact_integration
       
        accounts = partner_id.get_account_ids()
        
        self._sync_bank_accounts(accounts)           
        
        return {
        'name': _('Return To Bank Account'),
        'res_model': 'res.partner.bank',
        'view_mode': 'tree,form',
        'target': 'current',
        'type': 'ir.actions.act_window',
        }

    def _sync_bank_accounts(self, accounts):
        
        valid_bank_accounts = list(filter(lambda x: x.get('extra')['iban'], accounts))
        
        for account in valid_bank_accounts:
            
            partner_bank_id = self.env['res.partner.bank'].search([
                ('acc_number', '=', account.get('extra')['iban'])
            ], limit=1)
                        
            if partner_bank_id:
            
                partner_bank_id.write({
                    'acc_number': account.get('extra')['iban'],
                    'bank_id': self.bank_id.id,
                    'account_uuid': account.get('id')
                })
            
            else:
            
                partner_bank_id = self.env['res.partner.bank'].create({
                    'partner_id': self.env.company.id,
                    'acc_number': account.get('extra')['iban'],
                    'bank_id': self.bank_id.id,
                    'account_uuid': account.get('id')
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
