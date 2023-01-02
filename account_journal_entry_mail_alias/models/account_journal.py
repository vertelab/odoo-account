from odoo import models, fields, api, _
from odoo.tools import remove_accents
import logging
import re
import warnings

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _update_mail_alias(self, vals=None):
        if vals is not None:
            warnings.warn(
                '`vals` is a deprecated argument of `_update_mail_alias`',
                DeprecationWarning,
                stacklevel=2
            )
        self.ensure_one()
        if self.type in ('purchase', 'sale', 'general'):
            alias_values = self._get_alias_values(type=self.type, alias_name=self.alias_name)
            print(alias_values)
            if self.alias_id:
                self.alias_id.sudo().write(alias_values)
            else:
                alias_values['alias_model_id'] = self.env['ir.model']._get('account.move').id
                alias_values['alias_parent_model_id'] = self.env['ir.model']._get('account.journal').id
                self.alias_id = self.env['mail.alias'].sudo().create(alias_values)
        elif self.alias_id:
            self.alias_id.unlink()

    def _get_alias_values(self, type, alias_name=None):
        """ This function verifies that the user-given mail alias (or its fallback) doesn't contain non-ascii chars.
            The fallbacks are the journal's name, code, or type - these are suffixed with the
            company's name or id (in case the company's name is not ascii either).
        """

        def get_company_suffix():
            if self.company_id != self.env.ref('base.main_company'):
                try:
                    remove_accents(self.company_id.name).encode('ascii')
                    return '-' + str(self.company_id.name)
                except UnicodeEncodeError:
                    return '-' + str(self.company_id.id)
            return ''

        if not alias_name:
            alias_name = self.name
            alias_name += get_company_suffix()
        try:
            remove_accents(alias_name).encode('ascii')
        except UnicodeEncodeError:
            try:
                remove_accents(self.code).encode('ascii')
                safe_alias_name = self.code
            except UnicodeEncodeError:
                safe_alias_name = self.type
            safe_alias_name += get_company_suffix()
            _logger.warning("Cannot use '%s' as email alias, fallback to '%s'",
                            alias_name, safe_alias_name)
            alias_name = safe_alias_name
        alias_vals = {
            'alias_parent_thread_id': self.id,
            'alias_name': alias_name,
        }
        extra_move_vals = {'company_id': self.company_id.id, 'journal_id': self.id}
        if type == 'purchase':
            alias_vals['alias_defaults'] = {'move_type': 'in_invoice', **extra_move_vals}
        elif type == 'sale':
            alias_vals['alias_defaults'] = {'move_type': 'out_invoice', **extra_move_vals}
        elif type == 'general':
            alias_vals['alias_defaults'] = {'move_type': 'entry', **extra_move_vals}
        return alias_vals
