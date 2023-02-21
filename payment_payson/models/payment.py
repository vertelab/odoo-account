# coding: utf-8
import logging
from datetime import datetime
from dateutil import relativedelta
from odoo import api, exceptions, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)



class PaymentAcquirer(models.Model):
    """ Acquirer Model. Each specific acquirer can extend the model by adding
    its own fields, using the acquirer_name as a prefix for the new fields.
    Using the required_if_provider='<name>' attribute on fields it is possible
    to have required fields that depend on a specific acquirer.

    Each acquirer has a link to an ir.ui.view record that is a template of
    a button used to display the payment form. See examples in ``payment_ingenico``
    and ``payment_paypal`` modules.

    Methods that should be added in an acquirer-specific implementation:

     - ``<name>_form_generate_values(self, reference, amount, currency,
       partner_id=False, partner_values=None, tx_custom_values=None)``:
       method that generates the values used to render the form button template.
     - ``<name>_get_form_action_url(self):``: method that returns the url of
       the button form. It is used for example in ecommerce application if you
       want to post some data to the acquirer.
     - ``<name>_compute_fees(self, amount, currency_id, country_id)``: computes
       the fees of the acquirer, using generic fields defined on the acquirer
       model (see fields definition).

    Each acquirer should also define controllers to handle communication between
    OpenERP and the acquirer. It generally consists in return urls given to the
    button form and that the acquirer uses to send the customer back after the
    transaction, with transaction details given as a POST request.
    """
    _inherit = 'payment.acquirer'
    
    provider = fields.Selection(selection_add=[
        ('payson', 'Payson')
    ], ondelete={'payson': 'set default'})
    
    
    def payson_form_generate_values(self, values):
        # ~ base_url = self.get_base_url()

        # ~ paypal_tx_values = dict(values)
        # ~ paypal_tx_values.update({
            # ~ 'cmd': '_xclick',
            # ~ 'business': self.paypal_email_account,
            # ~ 'item_name': '%s: %s' % (self.company_id.name, values['reference']),
            # ~ 'item_number': values['reference'],
            # ~ 'amount': values['amount'],
            # ~ 'currency_code': values['currency'] and values['currency'].name or '',
            # ~ 'address1': values.get('partner_address'),
            # ~ 'city': values.get('partner_city'),
            # ~ 'country': values.get('partner_country') and values.get('partner_country').code or '',
            # ~ 'state': values.get('partner_state') and (values.get('partner_state').code or values.get('partner_state').name) or '',
            # ~ 'email': values.get('partner_email'),
            # ~ 'zip_code': values.get('partner_zip'),
            # ~ 'first_name': values.get('partner_first_name'),
            # ~ 'last_name': values.get('partner_last_name'),
            # ~ 'paypal_return': urls.url_join(base_url, PaypalController._return_url),
            # ~ 'notify_url': urls.url_join(base_url, PaypalController._notify_url),
            # ~ 'cancel_return': urls.url_join(base_url, PaypalController._cancel_url),
            # ~ 'handling': '%.2f' % paypal_tx_values.pop('fees', 0.0) if self.fees_active else False,
            # ~ 'custom': json.dumps({'return_url': '%s' % paypal_tx_values.pop('return_url')}) if paypal_tx_values.get('return_url') else False,
        # ~ })
        # ~ return paypal_tx_values
        return False
        
        
    def payson_compute_fees(self, amount, currency_id, country_id):
        """ Compute paypal fees.
            :param float amount: the amount to pay
            :param integer country_id: an ID of a res.country, or None. This is
                                       the customer's country, to be compared to
                                       the acquirer company country.
            :return float fees: computed fees
        """
        # ~ if not self.fees_active:
            # ~ return 0.0
        # ~ country = self.env['res.country'].browse(country_id)
        # ~ if country and self.company_id.sudo().country_id.id == country.id:
            # ~ percentage = self.fees_dom_var
            # ~ fixed = self.fees_dom_fixed
        # ~ else:
            # ~ percentage = self.fees_int_var
            # ~ fixed = self.fees_int_fixed
        # ~ fees = (percentage / 100.0 * amount + fixed) / (1 - percentage / 100.0)
        # ~ return fees
        return False
