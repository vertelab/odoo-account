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

from datetime import datetime
from lxml import etree

import logging
_logger = logging.getLogger(__name__)


class SebGetter(CurrencyGetterInterface):
    """Implementation of Currency_getter_factory interface
    for ECB service
    """
    code = 'SEB'
    name = 'SEB'
    supported_currency_array = [
        "AUD", "BGN", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP",
        "HKD", "HRK", "HUF", "IDR", "ILS", "INR", "JPY", "KRW", "LTL", "MXN",
        "MYR", "NOK", "NZD", "PHP", "PLN", "RON", "RUB", "SEK", "SGD", "THB",
        "TRY", "USD", "ZAR"]

    def get_updated_currency(self, currency_array, main_currency,
                             max_delta_days):
        """implementation of abstract method of Curreny_getter_interface"""
        _logger.warn('\n\ncurrency_array: %s\nmain_currency: %s\nmax_delta_days: %s' % (currency_array, main_currency,
                             max_delta_days))
        if main_currency != 'SEK':
            raise Warning(_("SEB currency rates only support SEK as the main currency!"))
        
        for currency in currency_array:
            self.updated_currency[currency] = 123.456

        return self.updated_currency, self.log_info


#------------------------------------
# ~ import requests
# ~ from lxml import html
# ~ import datetime

# ~ # convert date [d]d/[m]m to yyyy-mm-dd
# ~ def convert_date(dt):
    # ~ c_day, c_month = dt.split("/")
    # ~ now = datetime.datetime.now()
    # ~ now_month = now.month
    # ~ now_year = now.year
    # ~ #test for wrong year
    # ~ if now_month < int(c_month):
        # ~ now_year -= 1
    # ~ return datetime.datetime(now_year,int(c_month),int(c_day)).strftime("%Y-%m-%d")

# ~ def fill_currency_dict(c):
    # ~ return {'%s'%(c[1].text):{'country':c[0].text, 'buy_rate':float(c[2].text.replace(',','.')), 'sell_rate':float(c[3].text.replace(',','.')), 'date':convert_date(c[4].text)}}

# ~ def get_currencies(url,currencies):
    # ~ h = requests.get(url)
    # ~ currency_dict = {}
    
    # ~ tree = html.fromstring(h.text)

    # ~ for cur in currencies:
        # ~ n = tree.xpath("//td[text()='%s']"%(cur))   # <td...>EUR</td>
        # ~ p = n[0].getparent()                        # <tr>...</tr>
        # ~ c = p.getchildren()                         # list of td nodes
        # ~ currency_dict.update(fill_currency_dict(c))
    
    # ~ return currency_dict
    

# ~ currencies = ['EUR','NOK','USD']
# ~ url = 'https://seb.se/pow/apps/Valutakurser/avista_tot.asp'

# ~ if __name__ == '__main__':
    # ~ print get_currencies(url,currencies)

