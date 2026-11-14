import base64
import csv
import logging
from markupsafe import Markup
from datetime import datetime
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class EDIMessage(models.Model):
    _name = 'edi.message'
    _inherit = ['edi.message', 'mail.thread', 'mail.activity.mixin']

    state = fields.Selection([
        ('draft', 'Draft'), ('ongoing', 'On going'), ('done', 'Done'), ('error', 'Error')
    ], default='draft')

    def unpack(self):
        result = super().unpack()
        if result:
            return result

        # Handle SIE4 format
        if self._is_sie_4():
            return self._process_sie4()

        # Handle DATEV format
        payload_dict = self._parse_payload_to_dict()
        if payload_dict and payload_dict.get('is_datev'):
            return self._process_datev(payload_dict)

        return False

    def _process_sie4(self):
        """Process SIE4 format file"""
        try:
            # Create SIE wizard
            sie_wizard = self.env['account.sie'].create({
                "data": self.payload,
                "company_id": 1,
                "create_balance_posts": False,
            })

            # Cleanse and check import file
            data = sie_wizard.cleanse_with_fire(sie_wizard.data)
            checked, missing_accounts, missing_series, missing_periods = sie_wizard.check_import_file()

            _logger.info(f"SIE4 check: {checked=}, {missing_accounts=}, {missing_series=}, {missing_periods=}")

            if not checked:
                # Build error messages
                error_messages = []

                if missing_accounts:
                    accounts_list = Markup("<br/>").join([Markup(f'{m_ac[0]}: {m_ac[1]}') for m_ac in missing_accounts])
                    msg = Markup("<strong>Missing accounts:</strong><br/>") + accounts_list
                    error_messages.append(msg)

                if missing_series:
                    msg = Markup("<strong>Missing series:</strong><br/>") + Markup(", ").join(missing_series)
                    error_messages.append(msg)

                # if missing_periods:
                #     msg = Markup("<strong>Missing periods:</strong><br/>") + Markup(", ").join(missing_periods)
                #     error_messages.append(msg)

                # Post all errors to chatter
                full_error = Markup("<h4>SIE4 import validation failed:</h4>") + Markup("<br/><br/>").join(
                    error_messages)
                self.message_post(body=full_error, message_type='comment')
                self.state = 'error'
                return False

            # Validation passed, perform import
            try:
                sie_move_ids = sie_wizard.send_form()
                _logger.info(f"SIE4 import result: {sie_move_ids}")
                moves = sie_move_ids.get('res_ids')

                # Check if moves were actually created
                if not sie_move_ids or not moves:
                    error_msg = Markup("<h4>SIE4 import failed:</h4><p>No account moves were created</p>")
                    self.message_post(body=error_msg, message_type='comment')
                    self.state = 'error'
                    return False

                if not moves:
                    error_msg = Markup("<h4>SIE4 import failed:</h4><p>No account moves were created</p>")
                    self.message_post(body=error_msg, message_type='comment')
                    self.state = 'error'
                    return False

                # Success - build message with move links
                move_links = [
                    Markup('<a href="#" data-oe-model="account.move" data-oe-id="{id}">{name}</a>').format(
                        id=move.id,
                        name=move.name if move.name else move.id
                    )
                    for move in moves
                ]

                move_links_str = Markup(", ").join(move_links)
                body = Markup("<p>SIE4 import completed successfully: {}</p>").format(move_links_str)
                self.message_post(body=body, message_type='comment')
                self.state = 'done'

                return True

            except Exception as e:
                error_msg = Markup("<h4>SIE4 import failed:</h4><p>{}</p>").format(str(e))
                _logger.error(f"SIE4 import failed: {e}", exc_info=True)
                self.message_post(body=error_msg, message_type='comment')
                self.state = 'error'
                return False

        except Exception as e:
            error_msg = Markup("<h4>SIE4 processing error:</h4><p>{}</p>").format(str(e))
            _logger.error(f"SIE4 processing error: {e}", exc_info=True)
            self.message_post(body=error_msg, message_type='comment')
            self.state = 'error'
            return False


    def _process_datev(self, payload_dict):
        """Process DATEV format file"""
        try:
            # Check if we already created a move (idempotent)
            existing_move = None
            if self.res_model == 'account.move' and self.res_id:
                existing_move = self.env['account.move'].browse(self.res_id)
                if existing_move.exists() and existing_move.state == 'draft':
                    _logger.info(f"Found existing draft move {existing_move.name}, will update")
                else:
                    existing_move = None

            # Create or update move
            created_move = self._sync_account_move(
                datev_data=payload_dict,
                existing_move=existing_move
            )

            if not created_move:
                self.state = 'error'
                return False

            # Link the move to this EDI message
            self.res_model = 'account.move'
            self.res_id = created_move.id
            self.state = 'done'
            return True

        except Exception as e:
            error_msg = f"DATEV processing error:\n{str(e)}"
            _logger.error(error_msg, exc_info=True)
            self.message_post(body=error_msg, message_type='comment')
            self.state = 'error'
            return False

    def _set_message_type(self, message_type):
        if not self.message_format_id and message_type == 'EXTF':
            self.message_format_id = self.env.ref('account_move_directory.edi_message_format_datev_csv')

    def _is_sie_4(self):
        try:
            data = base64.decodebytes(self.payload or '').decode('cp437')
            if "#SIETYP 4" in data:
                self.message_format_id = self.env.ref('account_move_directory.edi_message_format_sie_4')
                return True
        except UnicodeDecodeError:
            return False

    def _is_datev(self, binary_data):
        text_data = None
        for encoding in ['iso-8859-1', 'windows-1252', 'utf-8']:
            try:
                text_data = binary_data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if not text_data:
            return False

        # Check if first line starts with EXTF
        first_line = text_data.strip().split('\n')[0]

        if first_line.startswith('EXTF'):
            _logger.info("DATEV file detected")
            self._set_message_type(message_type='EXTF')
            return True
        else:
            _logger.info("Not a DATEV file")
            return False

    def _parse_datev(self, binary_data):
        """
        Parse DATEV CSV file into standardized format
        Returns: dict with header info and parsed lines
        """
        # Decode with proper encoding
        text_data = None
        for encoding in ['iso-8859-1', 'windows-1252', 'utf-8']:
            try:
                text_data = binary_data.decode(encoding)
                _logger.info(f"Successfully decoded with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                continue

        if not text_data:
            raise Exception("Could not decode file")

        # Detect CSV dialect (delimiter, quoting, etc.)
        try:
            dialect = csv.Sniffer().sniff(text_data, delimiters=";,")
            _logger.info(f"Detected delimiter: '{dialect.delimiter}'")
        except csv.Error:
            dialect = csv.excel
            _logger.info("Could not detect dialect, using excel default")

        # Parse CSV
        lines = text_data.strip().split('\n')
        csv_reader = csv.reader(
            lines,
            delimiter=dialect.delimiter,
            quotechar=dialect.quotechar,
            quoting=csv.QUOTE_MINIMAL
        )

        # Line 1: EXTF header (metadata) - extract header info
        header_fields = next(csv_reader)
        header_info = self._parse_datev_header(header_fields)
        _logger.info(f"Header info: {header_info}")

        # Line 2: Column headers (skip it)
        column_headers = next(csv_reader)
        _logger.info(f"Skipped column headers")

        # Line 3+: Data rows
        parsed_lines = []
        for i, fields in enumerate(csv_reader, start=3):

            if len(fields) < 13:  # Skip invalid lines
                _logger.warning(f"Line {i} skipped: only {len(fields)} fields (need at least 13)")
                continue

            # Parse date (DDMM format + year from header)
            date_str = fields[9]  # Belegdatum (column 10)

            if date_str and len(date_str) == 4:
                day = date_str[:2]
                month = date_str[2:]
                full_date = f"{day}/{month}/{header_info['fiscal_year']}"
                try:
                    parsed_date = datetime.strptime(full_date, "%d/%m/%Y").date()
                except Exception as e:
                    _logger.warning(f"Line {i}: Could not parse date '{full_date}': {e}")
                    continue
            else:
                _logger.warning(f"Line {i} skipped: invalid date format '{date_str}'")
                continue

            # Parse amount (replace comma with dot for float conversion)
            amount_str = fields[0].replace(',', '.')

            try:
                amount = float(amount_str) if amount_str else 0.0
            except Exception as e:
                _logger.warning(f"Line {i}: Could not parse amount '{amount_str}': {e}")
                continue

            # Get account codes and indicator
            account_code = fields[6]  # Konto
            contra_account_code = fields[7]  # Gegenkonto
            indicator = fields[1]  # S or H

            # Get analytic accounts (columns 37-38 in DATEV)
            analytic_account_1 = fields[36] if len(fields) > 36 else None
            analytic_account_2 = fields[37] if len(fields) > 37 else None

            # Build parsed line
            parsed_line = {
                'line': i,
                'account': account_code,
                'contra_account': contra_account_code,
                'indicator': indicator,
                'debit': amount if indicator == 'S' else 0.0,
                'credit': amount if indicator == 'H' else 0.0,
                'date': parsed_date,
                'name': fields[13][:60] if len(fields) > 13 else '',
                'ref': fields[10] if len(fields) > 10 else '',
                'analytic_account_1': analytic_account_1,
                'analytic_account_2': analytic_account_2,
            }

            parsed_lines.append(parsed_line)

        _logger.info(f"Total parsed lines: {len(parsed_lines)}")

        return {
            'header': header_info,
            'lines': parsed_lines
        }

    def _parse_datev_header(self, header_fields):
        """
        Parse DATEV header line (EXTF line) to extract metadata
        """
        header_info = {
            'format_identifier': header_fields[0] if len(header_fields) > 0 else None,
            'format_version': header_fields[1] if len(header_fields) > 1 else None,
            'data_category_code': header_fields[2] if len(header_fields) > 2 else None,
            'data_category_name': header_fields[3] if len(header_fields) > 3 else None,
            'fiscal_year': header_fields[11] if len(header_fields) > 11 else str(datetime.now().year),
            'account_length': int(header_fields[12]) if len(header_fields) > 12 and header_fields[12] else 4,
            'period_start': header_fields[13] if len(header_fields) > 13 else None,
            'period_end': header_fields[14] if len(header_fields) > 14 else None,
            'company_number': header_fields[18] if len(header_fields) > 18 else None,
            'currency': header_fields[21] if len(header_fields) > 21 else 'EUR',
            # Look for journal name in header - commonly in description field or at the end
            # 'journal': header_fields[16] if len(header_fields) > 16 else None,
        }

        for field in reversed(header_fields):
            if field and field.strip():
                header_info['journal'] = field.strip()
                break

        return header_info

    def _get_journal_for_datev(self, header_info):
        """
        Find journal by name or code from DATEV header

        Args:
            header_info: dict with DATEV header metadata

        Returns:
            journal.id or False
        """
        AccountJournal = self.env['account.journal']
        journal_name = header_info.get('journal')

        if not journal_name:
            msg = "No journal name found in DATEV header"
            _logger.warning(msg)
            self.message_post(body=msg, message_type='comment')
            return False

        # Search by code (case-insensitive) or name (case-insensitive)
        journal = AccountJournal.search([
            ('company_id', '=', self.env.company.id),
            '|',
            ('code', '=ilike', journal_name),
            ('name', '=ilike', journal_name)
        ], limit=1)

        if journal:
            _logger.info(f"Found journal: {journal.name} (code: {journal.code})")
            return journal.id
        else:
            msg = f"Journal not found: '{journal_name}'. Please create a journal with this name or code."
            _logger.error(msg)
            self.message_post(body=msg, message_type='comment')
            return False

    def _parse_payload_to_dict(self):
        if not self.payload:
            _logger.warning("No payload to parse")
            return False

        try:
            # Decode the binary payload
            binary_data = base64.b64decode(self.payload)

            # Check if it's DATEV
            if not self._is_datev(binary_data):
                return False

            # Parse DATEV file
            datev_data = self._parse_datev(binary_data)

            # Find journal
            journal_id = self._get_journal_for_datev(datev_data['header'])

            if not journal_id:
                msg = "Failed to process DATEV file: No valid journal found"
                self.message_post(body=msg, message_type='comment')
                self.state = 'error'
                return False

            # Add journal to data (not to individual lines)
            datev_data['journal_id'] = journal_id

            _logger.info(f"Parsed {len(datev_data['lines'])} lines from DATEV file")

            return {
                'is_datev': True,
                'header': datev_data['header'],
                'lines': datev_data['lines'],
                'journal_id': journal_id
            }

        except Exception as e:
            msg = f"Error parsing DATEV payload: {str(e)}"
            _logger.error(msg, exc_info=True)
            self.message_post(body=msg, message_type='comment')
            self.state = 'error'
            return False

    def _sync_account_move(self, datev_data, existing_move=None):
        """
        Create ONE account.move with all lines from DATEV file
        Or update existing move with missing lines
        """
        AccountMove = self.env['account.move']
        AccountAccount = self.env['account.account']
        AnalyticAccount = self.env['account.analytic.account']

        journal_id = datev_data['journal_id']
        lines = datev_data['lines']
        company_id = self.env.company.id
        header = datev_data['header']

        if not lines:
            msg = "No lines to process from DATEV file"
            _logger.warning(msg)
            self.message_post(body=msg, message_type='comment')
            return False

        # Build speed dicts
        acc_speed_dict = {
            account['code'].upper(): account['id']
            for account in AccountAccount.search_read(
                [
                    ('company_ids', 'any', [('id', '=', company_id)]),
                    ('deprecated', '=', False),
                ],
                ['code'],
            )
        }

        # Analytic account speed dict
        analytic_speed_dict = {
            (analytic['code'] or analytic['name']).upper(): analytic['id']
            for analytic in AnalyticAccount.search_read(
                [('company_id', '=', company_id)],
                ['code', 'name']
            )
        }

        # Build enhanced lookup caches once (optimization)
        account_lookup = self._account_lookup(acc_speed_dict)
        analytic_lookup = self._account_lookup(analytic_speed_dict)

        # Track errors
        errors = []
        skipped_lines = []

        # Build all move lines
        move_lines = []
        existing_line_refs = set()

        # If updating existing move, get existing line refs to avoid duplicates
        if existing_move:
            existing_line_refs = set(
                line.ref for line in existing_move.line_ids if line.ref
            )
            _logger.info(f"Existing move has {len(existing_line_refs)} lines with refs")

        for line in lines:
            # Skip if this line was already added (idempotent check)
            line_ref = f"{line['ref']}-{line['line']}"
            if line_ref in existing_line_refs:
                _logger.info(f"Skipping line {line['line']}: already exists")
                continue

            # Find account IDs using optimized lookup
            account_id = self._match_account(line['account'], account_lookup)
            contra_account_id = self._match_account(line['contra_account'], account_lookup)

            if not account_id:
                error_msg = f"Line {line['line']}: Account not found - {line['account']}"
                _logger.error(error_msg)
                errors.append(error_msg)
                skipped_lines.append(line['line'])
                continue

            if not contra_account_id:
                error_msg = f"Line {line['line']}: Contra account not found - {line['contra_account']}"
                _logger.error(error_msg)
                errors.append(error_msg)
                skipped_lines.append(line['line'])
                continue

            # Match analytic accounts using optimized lookup
            analytic_1_id = None
            analytic_2_id = None

            if line.get('analytic_account_1'):
                analytic_1_id = self._match_account(line['analytic_account_1'], analytic_lookup)
                if not analytic_1_id:
                    _logger.warning(f"Line {line['line']}: Analytic account not found - {line['analytic_account_1']}")

            if line.get('analytic_account_2'):
                analytic_2_id = self._match_account(line['analytic_account_2'], analytic_lookup)
                if not analytic_2_id:
                    _logger.warning(f"Line {line['line']}: Analytic account not found - {line['analytic_account_2']}")

            # Create two move lines per DATEV line
            # Line 1: Main account
            move_line_1 = self._prepare_move_line(
                account_id=account_id,
                name=line['name'],
                debit=line['debit'],
                credit=line['credit'],
                ref=line_ref,
                analytic_1_id=analytic_1_id,
                analytic_2_id=analytic_2_id
            )

            # Line 2: Contra account (opposite debit/credit)
            move_line_2 = self._prepare_move_line(
                account_id=contra_account_id,
                name=line['name'],
                debit=line['credit'],  # Swapped
                credit=line['debit'],  # Swapped
                ref=line_ref,
                analytic_1_id=analytic_1_id,
                analytic_2_id=analytic_2_id
            )

            move_lines.append((0, 0, move_line_1))
            move_lines.append((0, 0, move_line_2))

        # Log errors if any lines were skipped
        if errors:
            error_summary = f"Skipped {len(skipped_lines)} line(s) due to missing accounts:\n" + "\n".join(errors[:10])
            if len(errors) > 10:
                error_summary += f"\n... and {len(errors) - 10} more errors"
            self.message_post(body=error_summary, message_type='comment')

        if not move_lines:
            error_msg = "No valid move lines to create"
            self.message_post(body=error_msg, message_type='comment')
            return False

        # Create or update the move
        try:
            if existing_move:
                # Add new lines to existing move
                existing_move.write({'line_ids': move_lines})
                move = existing_move
                _logger.info(f"Updated existing move {move.name} with {len(move_lines)} new lines")
                msg = f"Added {len(move_lines)} lines to existing move {move.name}"
                self.message_post(body=msg, message_type='comment')
            else:
                # Create new move
                # Use first line's date, or period_end from header
                move_date = lines[0]['date'] if lines else datetime.now().date()
                move_ref = f"DATEV-{header.get('company_number', 'import')}-{move_date}"

                move = AccountMove.create({
                    'journal_id': journal_id,
                    'date': move_date,
                    'ref': move_ref,
                    'line_ids': move_lines
                })
                move_link = Markup('<a href="#" data-oe-model="account.move" data-oe-id="{id}">{name}</a>').format(
                    id=move.id,
                    name=move.name if move.name else move.id
                )
                msg = Markup("<p>Created move {} with {} lines").format(move_link, len(move_lines))
                if skipped_lines:
                    msg += Markup(" (skipped {} line(s))").format(len(skipped_lines))
                msg += Markup("</p>")
                self.message_post(body=msg, message_type='comment')

            return move

        except Exception as e:
            error_msg = f"Failed to create/update move: {str(e)}"
            _logger.error(error_msg, exc_info=True)
            self.message_post(body=error_msg, message_type='comment')
            return False

    def _prepare_move_line(self, account_id, name, debit, credit, ref=None, analytic_1_id=None, analytic_2_id=None):
        """
        Prepare move line values with analytic distribution
        """
        line_name = name if name else '/'
        if ref:
            line_name = f"{line_name} - {ref}" if name else ref
        vals = {
            'account_id': account_id,
            'name': line_name,
            'debit': debit,
            'credit': credit,
            'ref': ref,  # Add ref to track which lines were already created
        }

        # Add analytic distribution if account is income/expense
        account = self.env['account.account'].browse(account_id)
        if account.account_type in ('income', 'income_other', 'expense',
                                    'expense_depreciation', 'expense_direct_cost'):
            # Build analytic distribution dict
            analytic_distribution = {}

            if analytic_1_id:
                analytic_distribution[str(analytic_1_id)] = 100.0

            if analytic_2_id:
                # If both exist, split 50/50
                if analytic_distribution:
                    analytic_distribution = {
                        str(analytic_1_id): 50.0,
                        str(analytic_2_id): 50.0
                    }
                else:
                    analytic_distribution[str(analytic_2_id)] = 100.0

            if analytic_distribution:
                vals['analytic_distribution'] = analytic_distribution

        return vals

    def _account_lookup(self, speed_dict):
        """
        Build enhanced lookup cache with code variations
        Returns: dict with all possible code variations
        """
        lookup = {}

        for code, account_id in speed_dict.items():
            # Add exact match
            lookup[code] = account_id

            # Add stripped version (61100000 -> 611000)
            stripped = code.rstrip('0')
            if stripped and stripped != code:
                lookup[stripped] = account_id

        return lookup

    def _match_account(self, account_code, lookup):
        """
        Match account code using pre-built lookup cache
        """
        if not account_code:
            return False

        account_code_upper = account_code.upper()

        # Try lookup cache first (includes exact and stripped matches)
        if account_code_upper in lookup:
            return lookup[account_code_upper]

        # Fallback: prefix match for cases like 611000 matching 611000XX
        for code, account_id in lookup.items():
            if code.startswith(account_code_upper):
                _logger.warning(
                    f"Approximate match: import account {account_code} "
                    f"matched with Odoo account {code}"
                )
                return account_id

        return False

