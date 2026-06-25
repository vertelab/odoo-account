"""Account Commodity Demo — processes purchase flow and generates PDF invoices."""
import base64
import io
import logging
from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── Main entry point (called from post_init_hook) ───────────────────────

    @api.model
    def _commodity_demo_load_purchase_flow(self):
        """Idempotent: confirm POs, validate receipts, create vendor bills + PDFs."""
        IrModelData = self.env['ir.model.data']
        xmlid = IrModelData._xmlid_to_res_id

        # Idempotency check
        existing_bill = self.env['account.move'].search([
            ('name', '=', 'INV-DEMO-001'),
        ], limit=1)
        if existing_bill:
            _logger.info('commodity_demo: purchase flow already loaded, skipping')
            return 0

        # 1. Fetch latest commodity prices (non-blocking)
        self._commodity_demo_fetch_prices()

        # 2. Process each PO
        count = 0
        for po_ref, inv_name, inv_date, due_date, ref, partial_lines in [
            ('account_commodity_demo.po_001', 'INV-DEMO-001',
             '2025-03-20', '2025-04-20', 'LEV-2025-0187',
             {'PLAT-CHEM-1L': (18.0, 20.0)}),  # partial: 18 of 20
            ('account_commodity_demo.po_002', 'INV-DEMO-002',
             '2025-03-14', '2025-04-14', 'LEV-2025-0155',
             {}),  # full receipt
            ('account_commodity_demo.po_003', 'INV-DEMO-003',
             '2025-03-02', '2025-04-01', 'LEV-2025-0102',
             {}),  # full receipt, mark paid
        ]:
            po_id = xmlid(po_ref)
            if not po_id:
                _logger.warning('commodity_demo: PO %s not found, skipping', po_ref)
                continue

            po = self.env['purchase.order'].browse(po_id)
            if po.state == 'draft':
                po.button_confirm()
                self.env.cr.commit()
                _logger.info('commodity_demo: %s confirmed', po.name)

            # Process receipt
            self._commodity_demo_process_receipt(po, partial_lines)

            # Create vendor bill
            bill = self._commodity_demo_create_bill(po, inv_name, inv_date, due_date, ref)
            if bill:
                self._commodity_demo_attach_pdf(bill, inv_name, po,
                                                  bool(partial_lines))
                if po_ref.endswith('po_003'):
                    bill.action_post()  # mark PO-003 as paid
                count += 1

        self.env.cr.commit()
        _logger.info('commodity_demo: loaded %d vendor bills with PDFs', count)
        return count

    # ── Helpers ────────────────────────────────────────────────────────────

    @api.model
    def _commodity_demo_fetch_prices(self):
        """Try to fetch current commodity prices; fall back to default values."""
        Commodity = self.env['product.commodity']
        commodities = Commodity.search([
            ('code', 'in', ['XAU', 'XAG']),
            ('active', '=', True),
        ])
        try:
            commodities._fetch_prices()
            self.env.cr.commit()
            _logger.info('commodity_demo: fetched live prices for %s',
                         ', '.join(commodities.mapped('code')))
        except Exception as e:
            _logger.warning('commodity_demo: live price fetch failed (%s), '
                            'using demo defaults', str(e))

    @api.model
    def _commodity_demo_process_receipt(self, po, partial_lines):
        """Confirm and validate the incoming stock picking for a PO.
        partial_lines: dict of {default_code: (received_qty, ordered_qty)}"""
        picking = self.env['stock.picking'].search([
            ('purchase_id', '=', po.id),
            ('state', 'not in', ('done', 'cancel')),
        ], limit=1)
        if not picking:
            _logger.warning('commodity_demo: no picking found for %s', po.name)
            return

        picking.action_confirm()

        has_partial = False
        for move in picking.move_ids:
            code = move.product_id.default_code
            if code in partial_lines:
                move.quantity = partial_lines[code][0]
                has_partial = True
            else:
                move.quantity = move.product_uom_qty
            move.picked = True

        result = picking.button_validate()
        if result:
            # Handle backorder wizard
            wizard_model = result.get('res_model')
            wizard_id = result.get('res_id')
            if wizard_model and wizard_id:
                wizard = self.env[wizard_model].browse(wizard_id)
                # Check if wizard has a process method
                if hasattr(wizard, 'process'):
                    wizard.process()
                elif hasattr(wizard, 'process_cancel_backorder'):
                    wizard.process_cancel_backorder()
                else:
                    # Just try to call any validate-like method
                    wizard.with_context(skip_backorder=False).process()
        self.env.cr.commit()
        status = 'partial' if has_partial else 'full'
        _logger.info('commodity_demo: %s receipt processed (%s)', po.name, status)

    @api.model
    def _commodity_demo_create_bill(self, po, name, inv_date, due_date, ref):
        """Create a vendor bill from a PO's received quantities."""
        # Gather received lines
        lines_vals = []
        for pol in po.order_line:
            qty = pol.qty_received
            if qty <= 0:
                continue
            account = pol.product_id.product_tmpl_id.categ_id.property_account_expense_categ_id
            if not account:
                account = self.env['account.account'].search([
                    ('account_type', '=', 'expense_direct_cost'),
                ], limit=1)
                if not account:
                    account = self.env['account.account'].search([
                        ('account_type', '=', 'expense'),
                    ], limit=1)
            lines_vals.append((0, 0, {
                'product_id': pol.product_id.id,
                'name': pol.name or pol.product_id.display_name,
                'quantity': qty,
                'price_unit': pol.price_unit,
                'account_id': account.id if account else False,
                'tax_ids': [(6, 0, pol.taxes_id.ids)],
            }))

        if not lines_vals:
            _logger.warning('commodity_demo: no received lines for %s', name)
            return False

        journal = self.env['account.journal'].search([
            ('type', '=', 'purchase'),
        ], limit=1)

        bill = self.with_context(
            check_move_validity=False,
            default_move_type='in_invoice',
        ).create({
            'move_type': 'in_invoice',
            'partner_id': po.partner_id.id,
            'invoice_date': inv_date,
            'invoice_date_due': due_date,
            'date': inv_date,
            'ref': ref,
            'name': name,
            'journal_id': journal.id if journal else False,
            'invoice_line_ids': lines_vals,
        })

        # Link bill to PO
        po.write({'invoice_ids': [(4, bill.id)]})
        return bill

    # ── PDF generation ─────────────────────────────────────────────────────

    @api.model
    def _commodity_demo_attach_pdf(self, bill, inv_number, po, partial=False):
        """Generate and attach a vendor bill PDF to the account.move."""
        try:
            pdf_buf = self._commodity_demo_generate_pdf(inv_number, po, partial)
            if pdf_buf:
                pdf_buf.seek(0)
                self.env['ir.attachment'].create({
                    'name': '%s.pdf' % inv_number,
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_buf.read()),
                    'res_model': 'account.move',
                    'res_id': bill.id,
                    'mimetype': 'application/pdf',
                    'description': 'Leverantörsfaktura — 3-way match demo',
                })
                _logger.info('commodity_demo: PDF attached to %s', inv_number)
                return True
        except Exception as e:
            _logger.error('commodity_demo: PDF generation failed for %s: %s',
                          inv_number, str(e))
        return False

    @api.model
    def _commodity_demo_generate_pdf(self, inv_number, po, partial=False):
        """Generate a realistic Swedish vendor bill PDF with reportlab."""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.lib.colors import HexColor, white, grey
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_RIGHT, TA_CENTER
            from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                             Table, TableStyle)
        except ImportError:
            _logger.warning('commodity_demo: reportlab not available')
            return None

        buf = io.BytesIO()

        DARK_BLUE = HexColor('#1a3a5c')
        LIGHT_BLUE = HexColor('#e8f0fa')
        BORDER = HexColor('#cccccc')
        LIGHT_GREY = HexColor('#f5f5f5')
        DARK_GREY = HexColor('#333333')

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle('DocTitle', fontSize=18, textColor=DARK_BLUE,
                                  spaceAfter=4, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('DocSubtitle', fontSize=10, textColor=grey,
                                  spaceAfter=2, fontName='Helvetica'))
        styles.add(ParagraphStyle('SectionHead', fontSize=11, textColor=DARK_BLUE,
                                  spaceAfter=6, spaceBefore=10, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle('Value', fontSize=9, textColor=DARK_GREY,
                                  fontName='Helvetica-Bold', leading=11))
        styles.add(ParagraphStyle('TableCell', fontSize=8.5, textColor=DARK_GREY,
                                  fontName='Helvetica', leading=11))
        styles.add(ParagraphStyle('TableCellRight', fontSize=8.5, textColor=DARK_GREY,
                                  fontName='Helvetica', alignment=TA_RIGHT, leading=11))
        styles.add(ParagraphStyle('TableCellBold', fontSize=8.5, textColor=DARK_GREY,
                                  fontName='Helvetica-Bold', leading=11))
        styles.add(ParagraphStyle('Total', fontSize=10, textColor=DARK_BLUE,
                                  fontName='Helvetica-Bold', alignment=TA_RIGHT))
        styles.add(ParagraphStyle('TableHeader', fontSize=8, textColor=white,
                                  fontName='Helvetica-Bold', alignment=TA_CENTER))
        styles.add(ParagraphStyle('Footer', fontSize=7, textColor=grey,
                                  fontName='Helvetica', alignment=TA_CENTER))

        COMPANY = 'Nordic Supplies AB'
        ORG = '559123-4567'
        ADDR = 'Industrivägen 42, 111 22 Stockholm'

        supplier = po.partner_id

        def header_footer(canvas, doc):
            canvas.saveState()
            w, h = A4
            canvas.setFillColor(DARK_BLUE)
            canvas.rect(0, h - 28*mm, w, 28*mm, fill=1, stroke=0)
            canvas.setFillColor(white)
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawString(15*mm, h - 17*mm, COMPANY)
            canvas.setFont('Helvetica', 7)
            canvas.drawString(15*mm, h - 22*mm,
                              '%s | Org.nr: %s' % (ADDR, ORG))
            canvas.setFillColor(BORDER)
            canvas.rect(0, 18*mm, w, 0.5, fill=1, stroke=0)
            canvas.setFillColor(grey)
            canvas.setFont('Helvetica', 6.5)
            canvas.drawString(15*mm, 12*mm,
                              '%s | %s | Org.nr: %s' % (COMPANY, ADDR, ORG))
            canvas.drawRightString(w - 15*mm, 12*mm,
                                   'Sida %s' % canvas.getPageNumber())
            canvas.restoreState()

        doc = SimpleDocTemplate(buf, pagesize=A4,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=32*mm, bottomMargin=22*mm)
        story = []

        # Title
        story.append(Paragraph('LEVERANTÖRSFAKTURA', styles['DocTitle']))
        story.append(Paragraph('Nr: %s' % inv_number, styles['DocSubtitle']))
        story.append(Paragraph('Datum: %s' % po.date_order, styles['Value']))
        story.append(Spacer(1, 4*mm))

        # From / To blocks
        from_rows = [
            Paragraph('Faktura från', styles['SectionHead']),
            Paragraph('<b>%s</b>' % supplier.name, styles['Value']),
            Paragraph(supplier.street or '', styles['Value']),
            Paragraph('%s %s' % (supplier.zip or '', supplier.city or ''),
                      styles['Value']),
            Paragraph('Org.nr: %s' % (supplier.vat or ''), styles['Value']),
        ]
        to_rows = [
            Paragraph('Faktura till', styles['SectionHead']),
            Paragraph('<b>%s</b>' % COMPANY, styles['Value']),
            Paragraph(ADDR, styles['Value']),
            Paragraph('Org.nr: %s' % ORG, styles['Value']),
        ]
        max_r = max(len(from_rows), len(to_rows))
        from_rows += [Paragraph('', styles['Value'])] * (max_r - len(from_rows))
        to_rows += [Paragraph('', styles['Value'])] * (max_r - len(to_rows))
        pt = Table([[l, r] for l, r in zip(from_rows, to_rows)],
                   colWidths=[85*mm, 85*mm])
        pt.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(pt)
        story.append(Spacer(1, 6*mm))

        # Line items
        story.append(Paragraph('Artiklar / Tjänster', styles['SectionHead']))
        headers = ['Art.nr', 'Beskrivning', 'Antal', 'Enhet', 'á-pris', 'Belopp']
        widths = [22*mm, 52*mm, 16*mm, 12*mm, 20*mm, 24*mm]
        header_row = [Paragraph(h, styles['TableHeader']) for h in headers]
        table_data = [header_row]

        subtotal = 0.0
        for pol in po.order_line:
            qty = pol.qty_received
            if qty <= 0:
                continue
            line_total = qty * pol.price_unit
            subtotal += line_total
            table_data.append([
                Paragraph(pol.product_id.default_code or '', styles['TableCell']),
                Paragraph(pol.name or pol.product_id.display_name, styles['TableCell']),
                Paragraph(str(int(qty)), styles['TableCellRight']),
                Paragraph('st', styles['TableCell']),
                Paragraph('%.2f kr' % pol.price_unit, styles['TableCellRight']),
                Paragraph('%.2f kr' % line_total, styles['TableCellRight']),
            ])

        vat = round(subtotal * 0.25, 2)
        total = subtotal + vat

        # Empty spacer
        table_data.append([Paragraph('', styles['TableCell']) for _ in range(6)])
        table_data.append([
            Paragraph('', styles['TableCell']) for _ in range(4)
        ] + [Paragraph('Delsumma:', styles['TableCellBold']),
             Paragraph('%.2f kr' % subtotal, styles['TableCellBold'])])
        table_data.append([
            Paragraph('', styles['TableCell']) for _ in range(4)
        ] + [Paragraph('Moms (25%):', styles['TableCell']),
             Paragraph('%.2f kr' % vat, styles['TableCell'])])
        table_data.append([
            Paragraph('', styles['TableCell']) for _ in range(4)
        ] + [Paragraph('ATT BETALA:', styles['TableCellBold']),
             Paragraph('%.2f kr' % total, styles['Total'])])

        t = Table(table_data, colWidths=widths, repeatRows=1)
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [white, LIGHT_GREY]),
        ]
        if partial:
            for i, pol in enumerate(po.order_line):
                if pol.qty_received < pol.product_uom_qty:
                    style_cmds.append(
                        ('BACKGROUND', (0, i+1), (-1, i+1), HexColor('#fff3cd')))
        total_idx = len(table_data) - 1
        style_cmds += [
            ('BACKGROUND', (0, total_idx), (-1, total_idx), LIGHT_BLUE),
            ('LINEABOVE', (0, total_idx-1), (-1, total_idx-1), 1, DARK_BLUE),
        ]
        t.setStyle(TableStyle(style_cmds))
        story.append(t)

        # Payment info
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph('Betalningsinformation', styles['SectionHead']))
        story.append(Paragraph('Förfallodatum: %s' % po.date_order, styles['Value']))
        story.append(Paragraph('Referens: %s' % inv_number, styles['Value']))
        if partial:
            story.append(Paragraph(
                '<i>OBS: Delleverans. Resterande artiklar levereras separat.</i>',
                styles['TableCell']))
        story.append(Paragraph(
            '<i>Tack för er order! Vid frågor, kontakta %s.</i>' % supplier.name,
            styles['TableCell']))

        doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
        return buf


def post_init_hook(env):
    """Post-install hook — processes purchase flow for commodity demo."""
    count = env['account.move']._commodity_demo_load_purchase_flow()
    if count:
        env.cr.commit()
        _logger.info('commodity_demo: post_init_hook completed (%d bills)', count)
