# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2019 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo.addons.currency_rate_update.services.currency_getter_interface import CurrencyGetterInterface
from odoo.exceptions import UserError

from datetime import datetime
import requests
from lxml import html

import logging
_logger = logging.getLogger(__name__)


class SebSellGetter(CurrencyGetterInterface):
    """Implementation of Currency_getter_factory interface
    for SEB service using sell prices
    """
    code = 'SEBs'
    name = 'SEB (sell)'
    supported_currency_array = [
        'AUD', 'BGN', 'DKK', 'EUR', 'HKD', 'INR', 'IDR', 'ISK', 'JPY', 'CAD',
        'CNY', 'HRK', 'MYR', 'MAD', 'MXN', 'NOK', 'NZD', 'PLN', 'RUB', 'SAR',
        'CHF', 'SGD', 'GBP', 'ZAR', 'KRW', 'THB', 'CZK', 'TRY', 'HUF', 'USD']

    def get_current_value(self, data):
        return data['sell_rate']
    
    def get_updated_currency(self, currency_array, main_currency, max_delta_days):
        """implementation of abstract method of Curreny_getter_interface"""
        def convert_date(dt):
            """Convert date [d]d/[m]m to yyyy-mm-dd"""
            c_day, c_month = dt.split("/")
            now = datetime.now()
            now_month = now.month
            now_year = now.year
            # test for wrong year
            if now_month < int(c_month):
                now_year -= 1
            return datetime(now_year, int(c_month), int(c_day))
        
        def fill_currency_dict(c):
            return {
                c[1].text: {
                    'country':c[0].text,
                    'buy_rate':float(c[2].text.replace(',','.')),
                    'sell_rate':float(c[3].text.replace(',','.')),
                    'date':convert_date(c[4].text)}}
        
        def get_currencies(url, currencies): 
            try:
                currency_dict = {}
                tree = html.fromstring(requests.get(url).text)
                for cur in currencies:
                    n = tree.xpath("//td[text()='%s']"%(cur))   # <td...>EUR</td>
                    p = n[0].getparent()                        # <tr>...</tr>
                    c = p.getchildren()                         # list of td nodes
                    currency_dict.update(fill_currency_dict(c))
                return currency_dict
            except IOError:
                raise UserError(
                    _('Web Service does not exist (%s)!') % url)
            except:
                raise

        url = 'https://seb.se/pow/apps/Valutakurser/avista_tot.asp'    
        
        if main_currency != 'SEK':
            msg = _("SEB currency rates only support SEK as the main currency!")
            self.log_info += "\n WARNING : %s" % msg
            _logger.warning(msg)
            return self.updated_currency, self.log_info
        
        for currency in currency_array:
            self.validate_cur(currency)
        for currency, data in get_currencies(url, currency_array).iteritems():
            self.check_rate_date(data['date'], max_delta_days)
            self.updated_currency[currency] = 1.0 / self.get_current_value(data)

        return self.updated_currency, self.log_info

class SebBuyGetter(SebSellGetter):
    """Implementation of Currency_getter_factory interface
    for SEB service using buy prices
    """
    code = 'SEBb'
    name = 'SEB (buy)'
    
    def get_current_value(self, data):
        return data['buy_rate']
