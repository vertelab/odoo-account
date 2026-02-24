import logging
import re
import base64
import eml_parser
import json
from markupsafe import Markup
from langchain_core.messages import AIMessage

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)

class AIQuest(models.Model):
    _inherit = "ai.quest"

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    ai_type = fields.Selection(selection_add=[('account-invoice', 'Invoice'),('account-invoice-pdf','Invoice PDF')], ondelete={'account-invoice': 'cascade', 'account-invoice-pdf': 'cascade'})

    def _serialize_ai_messages(self, ai_messages):
        filtered_messages = [msg for msg in ai_messages if msg.content.strip()]
        ai_invoice_data = []
        for ai_message in filtered_messages:
            if ai_message.content:
                json_data = self.json2dict(ai_message.content)
                if json_data:
                    ai_invoice_data.append(json_data)
        return ai_invoice_data

    def mail(self, mail, session):
        if not session.move_id:
            session.create_minimal_invoice()
        return super(AIQuest, self).mail(mail, session)

    def parse_invoice_data(self, res):
        ai_messages = [m for m in res.get('messages') if isinstance(m, AIMessage)]
        try:
            ai_invoice_data = self._serialize_ai_messages(ai_messages)[-1]
            invoice_data = ai_invoice_data.get('invoice')
            return invoice_data
        except IndexError:
            raise UserError("Error get the content from AI. Run this again.")

    def _get_or_create_partner(self, name):
        partner_id = self.env['res.partner'].search([('name', '=', name)], limit=1)
        if not partner_id:
            partner_id = self.env['res.partner'].create({
                'name': name,
                'company_type': 'company'
            })
        return partner_id.id

    def _get_currency(self, currency):
        currency_id = self.env['res.currency'].search([('name', '=', currency)], limit=1)
        if not currency_id:
            currency_id = self.env['res.currency'].search([('symbol', '=', currency)], limit=1)
        return currency_id.id
        
    def _prepare_vendor_bill(self, invoice_data, session, partner_id):
        if session.ai_quest_id.company_id:
            self = self.with_context(company_id=session.ai_quest_id.company_id.id)
        _logger.warning(f"{self.env.context=}")
        
        invoice_data = self._vendor_bill_vals(invoice_data, session, partner_id)
        
        #invoice_data.pop('invoice_line_ids', False)
        
        if session.move_id:
            session.move_id.write(invoice_data)
            move_id = session.move_id
        else:
            move_id = self.env['account.move'].create(invoice_data)
            session.move_id = move_id.id
        return move_id

    def _vendor_bill_vals(self, invoice_data, session, partner_id):
        customer_name = invoice_data.pop('customer', False)
        vendor_name = invoice_data.pop('vendor', False)
        vendor_in_eu = invoice_data.pop('vendor_in_eu', False)
        customer_in_eu = invoice_data.pop('customer_in_eu', False)
        currency = self._get_currency(
            invoice_data.pop('currency', 'SEK')
        )
        if not currency:
            currency = self.env['res.currency'].search([('name', '=', 'SEK')]).id
        #period_id = self.env['account.period'].date2period(
        #    invoice_data.get('date', fields.Date.today())
        #).id

        invoice_data['partner_id'] = partner_id.id if partner_id else False
        invoice_data['currency_id'] = currency
        #if period_id:
        #   invoice_data['period_id'] = period_id
        invoice_data['ai_session_id'] = session.id
        invoice_data['invoice_date'] = invoice_data.get('date')
        invoice_data['invoice_payment_term_id'] = partner_id.property_supplier_payment_term_id.id if partner_id else self.env.ref('account.account_payment_term_30days').id
        invoice_data['move_type'] = 'in_invoice'
        invoice_data['fiscal_position_id'] = partner_id.property_account_position_id.id if partner_id and partner_id.property_account_position_id else invoice_data.pop('fiscal_position_id', False)
        invoice_data['invoice_line_ids'] = self._invoice_lines(invoice_data.pop('invoice_line_ids', False), invoice_data['fiscal_position_id'])
        _logger.warning(f"odoo-account {invoice_data=}")
        session.invoice_metadata = invoice_data
        return invoice_data


    def _create_vendor_bill(self, invoice_data, session, partner_id):
        if session.ai_quest_id.company_id:
            self = self.with_context(company_id=session.ai_quest_id.company_id.id)
        _logger.warning(f"_create_vendor_bill {self.env.context=}")

        invoice_data = self._vendor_bill_vals(invoice_data, session, partner_id)
        
        if session.move_id:
            _logger.warning(f"{invoice_data=}")
            session.move_id.write(invoice_data)
            _logger.warning(f"{session.move_id.fiscal_position_id=}")
            move_id = session.move_id
        else:
            move_id = self.env['account.move'].create(invoice_data)
            session.move_id = move_id.id
        return move_id

    def _invoice_lines(self, invoice_lines, fiscal_position=None):
        company_id = self.env.context.get('company_id') or self.env.company.id
        default_journal = self.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', company_id)], limit=1)
        default_account = default_journal.default_account_id.id
        default_tax = self.env['res.company'].browse(company_id).account_purchase_tax_id.ids
        product_account = False
        product_tax = False
        dynamic_account_id = False
        dynamic_tax_id = False
        
        lines = []
        for line in invoice_lines:
            if product_name := line.get('name'):
               product_id = self.env['product.product'].search([('name','=', product_name)], limit=1)
               if product_id:
                  product_account = product_id.property_account_expense_id
                  product_tax = product_id.supplier_taxes_id
                  line['product_id'] = product_id.id

            if account_id := line.get('account_id'):
                dynamic_account_id = self.env['account.account'].search([
                    ('code', '=', account_id), ('company_ids', 'in', [company_id])
                ], limit=1)

            if tax := line.pop('tax/vat', False):
                dynamic_tax_id = self.env['account.tax'].search([('name', '=', tax), ('company_id', '=', company_id)])

             #Grab tax/account from product, else what the ai has returned and default to journal if all else is false.
            if product_account:
                line['account_id'] = product_account.id
            elif dynamic_account_id:
                line['account_id'] = dynamic_account_id.id
            else:
                 line['account_id'] = default_account
                 
            if product_tax:
               line['tax_ids'] = [(6, 0, product_tax.ids)]
            elif dynamic_tax_id:
                 line['tax_ids'] = [(6, 0, dynamic_tax_id.id)]
            else:
                line['tax_ids'] = [(6, 0, default_tax)]
            
            
            #The fiscal postion translation is not triggered for whatever reason so that why this is here.
            if fiscal_position:
               fiscal_position = self.env['account.fiscal.position'].browse(int(fiscal_position))
            
            if fiscal_position and line.get('tax_ids'):
               src_taxes = self.env['account.tax'].browse(line['tax_ids'][0][2])
               translated_taxes = fiscal_position.map_tax(src_taxes)
               line['tax_ids'] = [(6, 0, translated_taxes.ids)]
               
            if fiscal_position and line.get('account_id'):
               src_account = self.env['account.account'].browse(line['account_id'])
               translated_account = fiscal_position.map_account(src_account)
               line['account_id'] = translated_account.id
               
            
            lines.append((0, 0, line))
        return lines
        
        
    def map_tax(self, taxes):
        return self.env['account.tax'].browse(unique(
            tax_id
            for tax in taxes
            for tax_id in (self.tax_map or {}).get(tax.id, [tax.id])
        ))

    def map_account(self, account):
        return self.env['account.account'].browse((self.account_map or {}).get(account.id, account.id))

        
    def get_from_email(self, session) -> dict:
        result = {}
        session_eml_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'ai.quest.session'),
            ('res_id', '=', session.id),
            ('mimetype', '=', 'message/rfc822'),
        ], limit=1)
        if not session_eml_attachment:
            mail_message = self.env['mail.message'].search(
                [('model', '=', 'ai.quest.session'), ('res_id', '=', session.id)])
            if mail_message and mail_message.email_from:
                result = {'from': mail_message.email_from.split('<')[-1].split('>')[0]}
                _logger.warning(f"{result=}")
            return result
        ep = eml_parser.EmlParser()
        raw_attachment = base64.b64decode(session_eml_attachment.datas)
        parsed_eml = ep.decode_email_bytes(raw_attachment)
        result = parsed_eml.get('header')

        return result

    def get_pdf_text(self, session) -> dict:
        session_pdf_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'ai.quest.session'),
            ('res_id', '=', session.id),
            ('mimetype', '=', 'application/pdf'),
        ], limit=1)

        if session_pdf_attachment:
            pdf_content = session_pdf_attachment.get_pdf_content()
            return pdf_content
        else:
            return False
            
    def match_purchase_order(self, session, json_data, partner_id, file_content):
        partner_purchase_order = self.find_partner_purchase_order(
                partner=partner_id, file_content=file_content
            )
        if partner_purchase_order:
            if json_data:
                self._prepare_vendor_bill(json_data.get('invoice'), session, partner_id)
            
            partner_purchase_order_ref = self.env['purchase.bill.union'].search([
                ('purchase_order_id', '=', partner_purchase_order.id)], limit=1)
            _logger.info(f"{partner_purchase_order_ref=}")
            session.move_id.write({
                'purchase_vendor_bill_id': partner_purchase_order_ref.id,
                'purchase_id': partner_purchase_order_ref.purchase_order_id.id
            })
            
            context_copy = self.env.context.copy()
            context_copy.update({'check_move_period_validity': False})
            session.move_id.with_context(context_copy)._compute_purchase_auto_complete()
            session.move_id.ref = json_data.get('invoice', {}).get('ref')
            message = Markup(
                '<div class="o_mail_notification">Purchase order found: <a href="#" data-oe-model="%s" data-oe-id="%s">%s</a></div>') % (
                          partner_purchase_order._name,
                          partner_purchase_order.id,
                          partner_purchase_order.name
                      )
            session.move_id.message_post(
                body=message,
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )
            return session.move_id, partner_purchase_order
        else:
            return False, False

    # ~ def partner_search(self, email_info):
        # ~ """Search partner using email and returns an id"""
        # ~ partner_id = False
        # ~ if email_info:
            # ~ partner_id = self.env['res.partner'].search(
                # ~ [('email', '=', email_info.get('from')), ('is_company', '=', True)], limit=1)
            # ~ if not partner_id:
                # ~ partner_id = self.env['res.partner'].search([('email', '=', email_info.get('from'))], limit=1)
        # ~ return partner_id

    def partner_search(self, session, partner_json):
        partner_id = False
        try:
            json_dict = self.env['ai.quest'].custom_extract_json(partner_json)
        except Exception as e:
            _logger.warning(f"partner_create failed from {partner_json=} due to {e=}")
            return partner_id
        if json_dict.get('vat'):
            partner_id = self.env['res.partner'].search([('vat', '=', json_dict.get('vat'))], limit=1)
        return partner_id

    def partner_create(self, session, partner_json):
        partner_id = False
        try:
            json_dict = self.env['ai.quest'].custom_extract_json(partner_json)
        except Exception as e:
            _logger.warning(f"partner_create failed from {partner_json=} due to {e=}")
       
        if json_dict.get('name'):
            # Filter to only valid res.partner fields
            valid_fields = set(self.env['res.partner']._fields.keys())
            safe_dict = {k: v for k, v in json_dict.items() if k in valid_fields}
            
            if not safe_dict.get("company_type"):
                safe_dict['company_type'] = 'company'  # This field exists, so safe to add
            _logger.warning(f"1 {safe_dict=}")    
            if safe_dict.get("country_id"):
                country = self.env['res.country'].search([('code','=',safe_dict.get("country_id"))])
                safe_dict["country_id"] = country.id if country else False
            _logger.warning(f"2 {safe_dict=}")    
            partner_id = self.env['res.partner'].create(safe_dict)
        return partner_id

    def _process_file_content(self, session, partner_id, file_content, match_purchase_order=False):

        move_id = False
        quest_agent = False

        if partner_id:
           quest_agent = self.ai_agent_ids.filtered(
               lambda agent_rec:
               agent_rec.object_id and
               agent_rec.object_id.id == partner_id.id
           )
        if not quest_agent:
            quest_agent = self.ai_agent_ids.filtered(
                lambda agent_rec: agent_rec.ai_agent_id.generic_agent
            )

        json_content = quest_agent.ai_agent_id.trigger_prompt(
            quest=self,
            session=session,
            debug=self.debug,
            message=file_content,
        )

        json_data = self.custom_extract_json(json_content.content)

        if match_purchase_order:
            #Find purchase order instead and get lines from there.
            move_id, partner_purchase_order = self.match_purchase_order(session, json_data, partner_id, file_content)
            if move_id:
               return move_id
                
        if session.move_id.invoice_line_ids:
            #Already has lines so don't use ai to read the pdf and fill it.
            return session.move_id
            
        if not json_data:
            return False
            
        if json_data:
            move_id = self._create_vendor_bill(
                json_data.get('invoice'), session, partner_id
            )

        return move_id

    def _set_to_check_vendor_bill(self, move_id):
        _logger.warning("_set_to_check_vendor_bill")
        if move_id:
            move_ids = self.env['account.move'].search([('ref', '=', move_id.ref)]) - move_id
            if move_ids:
                move_id.write({'checked': False})
                move_id.write({'to_check_duplicate': True})
                # Create links for duplicate bills
                duplicate_links = [
                    Markup('<a href="#" data-oe-model="{model}" data-oe-id="{id}">{name}</a>').format(
                        model=duplicate._name,
                        id=duplicate.id,
                        name=duplicate.name if duplicate.name else duplicate.id
                    )
                    for duplicate in move_ids
                ]
                duplicate_links_str = Markup(", ").join(duplicate_links)
                
                # Build the body message
                body = Markup(_("Duplicate vendor bill(s) found: %s")) % duplicate_links_str
                
                # Post the message on the original move
                move_id.message_post(body=body)
            #TODO CHECK if period is closed or not. 
            # period = self.env['account.period'].search([('date_start','<=',move_id.date),('date_stop','>=',move_id.date)])
            # _logger.warning(f"{[('date_start','>=',move_id.date),('date_stop','<=',move_id.date)]}")
            # _logger.warning(f"{period=}")
            # if not period:
            #     body=f"After Ai scanning no period found for date: {move_id.date.strftime('%Y-%m-%d')}. Please check if the date and period is correct."
            #     move_id.write({'checked': False})
            #     move_id.write({'to_check_period': True})
            #     move_id.message_post(body=body)
            # elif period and period.state == "done":
            #     body=f"After Ai scanning the period found for date: {move_id.date.strftime('%Y-%m-%d')} is closed. Please check if the date and period is correct."
            #     move_id.write({'checked': False})
            #     move_id.write({'to_check_period': True})
            #     move_id.message_post(body=body)
            

    def find_partner_based_on_vat(self, file_content):
        partner_id = self.company_id.partner_id.id
        partners_with_vat = self.env['res.partner'].search_read(
            [('is_company', '=', True), ('vat', '!=', False),('id','!=',partner_id)],
            ['id', 'name', 'vat']
        )
        for partner in partners_with_vat:
            if partner.get('vat') in file_content:
                _logger.warning(f"partner found {partner=}")
                return self.env['res.partner'].browse(partner.get('id'))
        return None

    def find_partner_based_on_keyword(self, file_content):
        if not file_content:  # Check if file_content is empty or None
            return None

        partners_with_keywords = self.env['res.partner'].search_read(
            [('is_company', '=', True), ('keywords', '!=', False)],
            ['id', 'name', 'keywords']
        )

        best_partner = None
        most_matches = 0

        for partner in partners_with_keywords:
            keywords = partner.get('keywords', '')
            if not keywords:  # Skip if keywords is None or empty
                continue

            partner_keyword = []
            for keyword in keywords.split(','):
                keyword = keyword.strip()
                if keyword and keyword in file_content:
                    _logger.warning(f"keyword found for {partner.get('name')}")
                    partner_keyword.append(keyword)

            # Find partner with the highest number of keyword matches
            if len(partner_keyword) > most_matches:
                most_matches = len(partner_keyword)
                best_partner = self.env['res.partner'].browse(partner.get('id'))

        return best_partner

    def find_partner_purchase_order(self, partner, file_content):
        if not partner:
           return None
        partner_purchase_orders_not_billed = self.env['purchase.order'].search(
            [('partner_id', '=', partner.id), ('invoice_status', '!=', 'invoiced'), ('state','!=','draft'), ('state','!=','cancel')])
            
        for partner_purchase_order in partner_purchase_orders_not_billed:
            if partner_purchase_order.name in file_content:
                _logger.info(
                    f"found purchase order: {partner_purchase_order.name=} - {partner_purchase_order.partner_id.name=}"
                )
                return partner_purchase_order
        
        partner_purchase_orders_billed_but_not_recieved = self.env['purchase.order'].search(
            [('partner_id', '=', partner.id), ('invoice_status', '=', 'invoiced'), ('reception_status', '!=', 'received'), ('state','!=','draft'), ('state','!=','cancel')])
        
        for partner_purchase_order in partner_purchase_orders_billed_but_not_recieved:
            if partner_purchase_order.name in file_content:
                _logger.info(
                    f"found purchase order: {partner_purchase_order.name=} - {partner_purchase_order.partner_id.name=}"
                )
                return partner_purchase_order
                
        return None

    def custom_extract_json(self, json_str):
        # Find JSON-like content within triple backticks
        pattern = r'(\{.*\})'
        match = re.search(pattern, json_str, re.DOTALL)

        if match:
            result = match.group(1)
            result = json.loads(result)
            #result = eval(result)
            if result.get('invoice',False) and result.get('invoice',False).get('invoice_line_ids'):
               for line in result.get('invoice',False).get('invoice_line_ids'):
                    if line.get('price_unit'):
                       line['price_unit'] = self.fix_number(str(line['price_unit']))
                    if line.get('quantity'):
                       line['quantity'] = self.fix_number(str(line['quantity']))
                    
            _logger.warning(f"{result}")
            return result
            
        return False
        
    def fix_number(self,num):
        comma_used_as_decimal_seprator = False
        if "," in num or "." in num:
            last_symbol = self.find_last_symbol(num)
            fixed_num = fixed_num = f"{''.join(num.split(last_symbol)[0:-1]).replace(',','').replace('.','')}.{num.split(last_symbol)[-1]}"
            return float(fixed_num.replace(" ",""))
        else:
            return float(num.replace(" ","")) if num else 0
            
    def find_last_symbol(self,num):
        # Iterate over the string in reverse order
        for char in reversed(num):
            # Check if the character is a comma or a dot
            if char == ',' or char == '.':
                return char  # Return the last non-numeric symbol
        return None  # Return None if no comma or dot is found


    def _check_purchase_order_is_delivered(self, partner_purchase_order):
        #if partner_purchase_order.amount_total == 0:
        #    return False
        if partner_purchase_order.reception_status != "received" and partner_purchase_order != "invoiced":
           return False
        return True


