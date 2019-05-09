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

from datetime import datetime, time
from zeep import Client

import logging
_logger = logging.getLogger(__name__)

import traceback

class SebSellGetter(CurrencyGetterInterface):
    """Implementation of Currency_getter_factory interface
    for SWEA service using sell prices
    """
    code = 'SWEAs'
    name = 'SWEA (sell)'
    supported_currency_array = [
        'AUD', 'BGN', 'DKK', 'EUR', 'HKD', 'INR', 'IDR', 'ISK', 'JPY', 'CAD',
        'CNY', 'HRK', 'MYR', 'MAD', 'MXN', 'NOK', 'NZD', 'PLN', 'RUB', 'SAR',
        'CHF', 'SGD', 'GBP', 'ZAR', 'KRW', 'THB', 'CZK', 'TRY', 'HUF', 'USD']
    
    def get_updated_currency(self, currency_array, main_currency, max_delta_days):
        """implementation of abstract method of Curreny_getter_interface"""
        def get_currencies(url, currencies): 
            try:
                currency_dict = {}
                ## consume
                client = Client(url)
                response = client.service.getLatestInterestAndExchangeRates("sv",["SEK%sPMI"%c for c in currencies])
                
                # per currency
                series = response["groups"][0]["series"] #list

                for cur in currencies:
                    seriesid = "SEK%sPMI"%cur
                    cur_item = filter(lambda item: item["seriesid"][:9] == seriesid, series)[0]
                    #cur_item = item for item in series if item["seriesid"] == seriesid
                    unit = cur_item["unit"]
                    resultrows = cur_item["resultrows"][0]
                    
                    rate = resultrows["value"]/unit
                    date = datetime.combine(resultrows["date"], time(0, 0))
                    d = {cur:{'rate':rate,'date':date}}
                    currency_dict.update(d)
                return currency_dict
            except IOError:
                raise UserError(
                    _('Web Service does not exist (%s)!') % url)
            except:
                raise
        url = "https://swea.riksbank.se/sweaWS/wsdl/sweaWS_ssl.wsdl"    
        
        if main_currency != 'SEK':
            msg = _("SWEA currency rates only support SEK as the main currency!")
            self.log_info += "\n WARNING : %s" % msg
            _logger.warning(msg)
            return self.updated_currency, self.log_info
        
        for currency in currency_array:
            self.validate_cur(currency)
        for currency, data in get_currencies(url, currency_array).iteritems():
            self.check_rate_date(data['date'], max_delta_days)
            self.updated_currency[currency] = 1.0 / data['rate']

        return self.updated_currency, self.log_info

