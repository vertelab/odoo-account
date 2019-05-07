# -*- coding: utf-8 -*-
# Copyright 2009-2016 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import xlwt
from openerp.addons.account_financial_report_webkit.report.open_invoices \
    import PartnersOpenInvoicesWebkit
from openerp.addons.account_financial_report_webkit_xls.report.open_invoices_xls import OpenInvoicesXls


class OpenInvoicesXls(OpenInvoicesXls):
    
    def generate_xls_report(self, _p, _xs, data, objects, wb):  # main function
        
        account_selection_ids = objects.env['account.account'].browse(data.get('form', {}).get('accounts_ids', []))
        # Initializations
        self.global_initializations(wb, _p, xlwt, _xs, objects, data)
        row_pos = 0
        # Print Title
        row_pos = self.print_title(_p, row_pos)
        # Print empty row to define column sizes
        row_pos = self.print_empty_row(row_pos)
        # Print Header Table titles (Fiscal Year - Accounts Filter - Periods
        # Filter...)
        row_pos = self.print_header_titles(_p, data, row_pos)
        # Print Header Table data
        row_pos = self.print_header_data(_p, data, row_pos)
        # Freeze the line
        self.ws.set_horz_split_pos(row_pos)
        # Print empty row
        row_pos = self.print_empty_row(row_pos)

        for acc in account_selection_ids or objects:
            if hasattr(acc, 'grouped_ledger_lines'):
                # call xls equivalent of
                # "grouped_by_curr_open_invoices_inclusion.mako.html"
                row_pos = self.print_grouped_line_report(
                    row_pos, acc, _xs, xlwt, _p, data)
            else:
                # call xls equivalent of "open_invoices_inclusion.mako.html"
                row_pos = self.print_ledger_lines(
                    row_pos, acc, _xs, xlwt, _p, data)
            row_pos += 1


report_parser = OpenInvoicesXls('report.account.account_report_open_invoices_xls',
                'account.account', parser=PartnersOpenInvoicesWebkit, register = False)
report_parser._reports['report.account.account_report_open_invoices_xls'] = report_parser
