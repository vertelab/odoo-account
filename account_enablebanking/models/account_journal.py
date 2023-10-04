import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timezone, timedelta
import requests
from pprint import pprint

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def action_sync_transactions_with_enable_banking(self):
        return {
            'name': _('Enable Banking Transaction'),
            'res_model': 'enable.banking.transaction.wizard',
            'view_mode': 'form',
            'context': {
                'default_journal_id': self.id,
                'default_account_uuid': self.bank_account_id.account_uuid,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def action_sync_balances_with_enable_banking(self):
        api_url, private_key, application_id, base_headers = self.env.user.company_id.request_essentials()
        account_uid = self.bank_account_id.account_uuid
        account_balance = requests.get(f"{api_url}/accounts/{account_uid}/balances", headers=base_headers)
        if account_balance.status_code == 200:
            _logger.info(f'Enable Banking Balances {account_balance.json()}')
        else:
            _logger.error(f"Error response {account_balance.status_code}: {account_balance.text}", )
            return False


class EnableBankingTransactions(models.TransientModel):
    _name = "enable.banking.transaction.wizard"

    journal_id = fields.Many2one('account.journal', string="Journal")

    account_uuid = fields.Char(string="Account UUID")

    date_from = fields.Date(string="From", default=fields.Date.today)

    date_to = fields.Date(string="To", default=fields.Date.today)

    def _fetch_transactions(self):
        api_url, private_key, application_id, base_headers = self.env.user.company_id.request_essentials()
        query = {
            # "date_from": (datetime.now(timezone.utc) - timedelta(days=90)).date().isoformat(),
            "date_from": self.date_from,
            "date_to": self.date_to
        }

        continuation_key = None
        transactions = []
        while True:
            if continuation_key:
                query["continuation_key"] = continuation_key
            account_transaction = requests.get(
                f"{api_url}/accounts/{self.account_uuid}/transactions",
                params=query,
                headers=base_headers,
            )
            resp_data = account_transaction.json()
            if account_transaction.status_code == 200:
                # _logger.info('Enable Banking Transactions %s', resp_data.get("transactions"))
                transactions.extend(resp_data.get("transactions", []))
                continuation_key = resp_data.get("continuation_key")
                if not continuation_key:
                    _logger.info("No continuation key. All transactions were fetched")
                    break
                _logger.info(f"Going to fetch more transactions with continuation key {continuation_key}")
            else:
                _logger.error(f"Error response {resp_data.get('code')}: {resp_data.get('message')}")
                raise ValidationError(
                    f"There is a problem fetching account transaction. "
                    f"Error response {resp_data.get('code')}: {resp_data.get('message')}"
                )

        return transactions  # Return the transactions list if needed

    def action_sync_transactions(self):
        transactions = self._fetch_transactions()

        bank_statement_id = self.env['account.bank.statement'].search([
            ('name', '=', f"{self.date_from} - {self.date_to}")
        ])

        if not bank_statement_id:
            bank_statement_id = self.env['account.bank.statement'].create({
                'journal_id': self.journal_id.id,
                'name': f"{self.date_from} - {self.date_to}"
            })

        for transaction in transactions:
            partner_id = False

            bank_statement_line_id = self.env['account.bank.statement.line'].search([
                ('payment_ref', '=', transaction.get('entry_reference'))
            ])
            if not bank_statement_line_id:
                if transaction.get('creditor'):
                    partner_id = self._sync_partner(transaction.get('creditor')['name']).id
                if transaction.get('credit_debit_indicator') == 'CRDT':
                    amount = float(transaction.get('transaction_amount')['amount'])
                else:
                    amount = -float(transaction.get('transaction_amount')['amount'])

                currency_id = self.env['res.currency'].search([
                    ('name', '=', transaction.get('transaction_amount')['currency'])])
                if currency_id != self.journal_id.currency_id:
                    raise UserError(_(
                        f"The Bank Account {self.journal_id.bank_account_id.acc_number} "
                        f"has transaction with a different currency ({currency_id.name}) to the journal "
                        f"({self.journal_id.currency_id}). They need to be the same."))

                self.env['account.bank.statement.line'].create({
                    'date': transaction.get('transaction_date'),
                    'invoice_date': transaction.get('booking_date'),
                    'amount': amount,
                    'narration': transaction.get('remittance_information')[-1],
                    'transaction_type': transaction.get('credit_debit_indicator'),
                    'ref': transaction.get('reference_number'),
                    'partner_id': partner_id,
                    'payment_ref': transaction.get('entry_reference'),
                    'statement_id': bank_statement_id.id,

                })

    def _sync_partner(self, partner_name):
        partner_id = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if not partner_id:
            partner_id = self.env['res.partner'].create({
                'name': partner_name
            })
        return partner_id


class EnableBanking(models.TransientModel):
    _name = "enable.banking.wizard"
    _description = "Enable Banking Wizard"
    _rec_name = 'code'

    bank_id = fields.Many2one("res.bank", string="Bank")
    code = fields.Char(string="Code")
    session_id = fields.Char(string="Session ID")
    date_from = fields.Date(string="From", default=fields.Date.today)
    date_to = fields.Date(string="To", default=fields.Date.today)

    def sync_accounts(self):
        if not self.bank_id:
            raise ValidationError(_("Select a Bank!"))
        self._create_session()

    def _create_session(self):
        api_url, private_key, application_id, base_headers = self.env.user.company_id.request_essentials()
        session = requests.post(f"{api_url}/sessions", json={"code": self.code}, headers=base_headers)
        session_resp = session.json()
        if session.status_code == 200:
            self._sync_bank_accounts(session_resp.get('accounts'))
            return session.json()
        else:
            _logger.error(f"Error response {session_resp.get('code')}: {session_resp.get('message')}")
            raise ValidationError("There is a problem creating session.")

    def _sync_bank_accounts(self, accounts):
        valid_bank_accounts = list(filter(lambda x: x.get('account_id')['iban'], accounts))
        for account in valid_bank_accounts:
            partner_bank_id = self.env['res.partner.bank'].search([
                ('acc_number', '=', account.get('account_id')['iban'])
            ], limit=1)
            if partner_bank_id:
                partner_bank_id.write({
                    'partner_id': self._sync_partner(account.get('name')).id,
                    'acc_number': account.get('account_id')['iban'],
                    'bank_id': self.bank_id.id,
                    'account_uuid': account.get('uid')
                })
            else:
                self.env['res.partner.bank'].create({
                    'partner_id': self._sync_partner(account.get('name')).id,
                    'acc_number': account.get('account_id')['iban'],
                    'bank_id': self.bank_id.id,
                    'account_uuid': account.get('uid')
                })

    def _sync_partner(self, partner_name):
        partner_id = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if not partner_id:
            partner_id = self.env['res.partner'].create({
                'name': partner_name
            })
        return partner_id
