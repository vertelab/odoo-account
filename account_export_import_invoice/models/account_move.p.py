from odoo import fields, models, api, _
from odoo.exceptions import UserError
import base64
from lxml import etree

ACCOUNT_MOVE_FIELDS = ['name', 'partner_id', 'invoice_date', 'journal_id', 'invoice_line_ids']

ACCOUNT_MOVE_LINE_FIELDS = [
    'product_id', 'name', 'account_id', 'move_id', 'quantity', 'price_unit', 'tax_ids', 'price_subtotal'
]


class Partner(models.Model):
    _inherit = "account.move"

    def _get_account_move_fields(self, model, filter_func):
        return self.env['ir.model.fields'].search([
            ('model_id.model', '=', model)
        ]).filtered(filter_func)

    def _get_account_move_line_fields(self, model, filter_func):
        return self.env['ir.model.fields'].search([
            ('model_id.model', '=', model)
        ]).filtered(filter_func)

    def _process_field_data(self, etree_field, field, rec):
        if field.ttype in ['selection', 'char', 'date']:
            etree_field.text = str(getattr(rec, field.name))
        if field.ttype == 'many2one':
            if field.name == 'account_id':
                etree_field.text = str(getattr(rec, field.name).code)
            else:
                etree_field.text = str(getattr(rec, field.name).name)
        if field.ttype in ['one2many', 'many2many']:
            relation_field_ids = self._get_account_move_line_fields(
                model=field.relation,
                filter_func=lambda r_field: r_field.name in ACCOUNT_MOVE_LINE_FIELDS,
            )
            for line in rec[field.name]:
                print("line", line, rec[field.name])
                if field.name == 'tax_ids':
                    tree_line = etree.SubElement(etree_field, 'line')
                    tree_line.text = str(line.name)
                else:
                    tree_line = etree.SubElement(etree_field, 'line')
                    for relation_field_id in relation_field_ids:
                        if line[relation_field_id.name]:
                            # field.ttype in ['one2many', 'many2many']:
                            if relation_field_id.ttype == ['many2one', 'many2many']:
                                etree.SubElement(tree_line, relation_field_id.name).text = str(
                                    line[relation_field_id.name].id
                                )
                            # elif relation_field_id.ttype == 'many2one':
                            #     etree.SubElement(tree_line, relation_field_id.name).text = str(
                            #         line[relation_field_id.name].id
                            #     )
                            else:
                                print("line[relation_field_id.name]", line[relation_field_id.name])
                                etree.SubElement(tree_line, relation_field_id.name).text = str(
                                    line[relation_field_id.name]
                                )

    def action_export_account_move(self):
        if not self.env.context.get('active_id'):
            raise UserError("No active Record")

        account_move_id = self.env['account.move'].browse(self.env.context.get('active_id')).exists()

        _fields = self._get_account_move_fields(
            model='account.move',
            filter_func=lambda module: module.modules == 'account',
        )

        data = etree.Element("move")

        for field in _fields.filtered(lambda x: x.name in ACCOUNT_MOVE_FIELDS):
            if account_move_id[field.name]:
                etree_field = etree.SubElement(data, field.name)
                self._process_field_data(etree_field, field, account_move_id)

        # if res_partner_id.invoice_import_count:
        #     self._import_configuration(data, res_partner_id)
        return self._export_attachment(data, account_move_id)

    def _export_attachment(self, data, account_move_id):
        xml_data = etree.tostring(data, pretty_print=True, xml_declaration=True, encoding='utf-8').decode('utf-8')
        attachment = self.env['ir.attachment'].create({
            'name': f"{account_move_id.name.replace('/', '-')}_config.xml",
            'datas': base64.encodebytes(xml_data.encode('utf-8')),
            'mimetype': 'application/xml',
        })

        return {
            'type': 'ir.actions.act_url',
            'name': attachment.name,
            'url': f'/web/content/ir.attachment/{attachment.id}/datas/{attachment.name}?download=true',
        }