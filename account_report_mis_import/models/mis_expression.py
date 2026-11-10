# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""MIS expression -> account.report.expression converter.

Pure functions, no database access, so every rule can be unit-tested against
the exact strings that exist in the Swedish data files.

The MIS grammar (``mis_builder/models/aep.py:136``)::

    (?P<field>\\bbal|\\bpbal|\\bnbal|\\bcrd|\\bdeb|\\bfld)
    (?P<mode>[piseu])?
    (?P<fld_name>\\.[a-zA-Z0-9_]+)?
    \\s*
    (?P<account_sel>_[a-zA-Z0-9]+|\\[.*?\\])
    \\s*
    (?P<ml_domain>\\[.*?\\])?

Two things that surprise people, both verified in the source:

* ``balp`` is **not** a field. It is ``bal`` + mode ``p``, and
  ``MODE_VARIATION = "p"`` means "movement in the period". It maps to
  ``date_scope="strict_range"``, which is already the default.
* ``crd`` returns the raw **credit** sum, not credit minus debit. A credit
  note lands on the debit side and is therefore invisible to ``crd`` -- which
  is why the old VAT report lost credit notes. The converter emits the domain
  as-is and flags the expression so this is visible during review.
"""

import ast
import json
import logging
import re

_logger = logging.getLogger(__name__)

# The accounting variable, exactly as MIS defines it.
MIS_ACC_RE = re.compile(
    r"(?P<field>\bbal|\bpbal|\bnbal|\bcrd|\bdeb|\bfld)"
    r"(?P<mode>[piseu])?"
    r"(?P<fld_name>\.[a-zA-Z0-9_]+)?"
    r"\s*"
    r"(?P<account_sel>_[a-zA-Z0-9]+|\[.*?\])"
    r"\s*"
    r"(?P<ml_domain>\[.*?\])?"
)

# Field -> what it means for the row total. Only 'bal' and 'crd'/'deb' can be
# expressed as an account.report engine; the rest need review.
SUPPORTED_FIELDS = ('bal', 'pbal', 'nbal', 'crd', 'deb')

# Engine chosen per pattern.
ENGINE_ACCOUNT_CODES = 'account_codes'
ENGINE_DOMAIN = 'domain'
ENGINE_AGGREGATION = 'aggregation'
ENGINE_CUSTOM = 'custom'

# How confident the conversion is. 'manual' entries must be reviewed by a human
# before the source module is retired.
CONFIDENCE_EXACT = 'exact'
CONFIDENCE_REVIEW = 'manual'
CONFIDENCE_UNPARSED = 'unparsed'


class Conversion(object):
    """One conversion result: what to write, and how much to trust it."""

    __slots__ = ('engine', 'formula', 'subformula', 'date_scope',
                 'confidence', 'note')

    def __init__(self, engine, formula, subformula=None, date_scope=None,
                 confidence=CONFIDENCE_EXACT, note=''):
        self.engine = engine
        self.formula = formula
        self.subformula = subformula
        self.date_scope = date_scope
        self.confidence = confidence
        self.note = note

    def __repr__(self):
        return '<Conversion %s %r (%s)>' % (
            self.engine, self.formula, self.confidence)

    def as_dict(self):
        return {
            'engine': self.engine,
            'formula': self.formula,
            'subformula': self.subformula,
            'date_scope': self.date_scope,
            'confidence': self.confidence,
            'note': self.note,
        }


# ----------------------------------------------------------------------
# Account selector parsing
# ----------------------------------------------------------------------
def _split_account_selector(selector):
    """'[3000, 3001, 3500-3599]' -> ['3000', '3001', '3500-3599'].

    MIS also accepts numbers written with spaces and an optional trailing
    ``* -1``. Returns a list of raw code tokens.
    """
    inner = selector.strip()
    if inner.startswith('[') and inner.endswith(']'):
        inner = inner[1:-1]
    tokens = []
    for token in inner.split(','):
        token = token.strip()
        if not token:
            continue
        # MIS accepts a trailing '%' meaning "every code starting with this"
        # (bal[3%,4%] = classes 3 and 4, bal[48%] = accounts 48xx).
        # account_codes expresses the same thing as a bare prefix, so the '%'
        # is dropped -- keeping it makes the account_codes parser reject the
        # WHOLE formula, which silently zeroes the row.
        #
        # Note the double '%%': MIS data files are read through a %-formatting
        # layer, so a literal percent is written twice and arrives here as a
        # single '%'. Strip every trailing '%' rather than exactly one.
        token = token.rstrip('%')
        if token:
            tokens.append(token)
    return tokens


def _codes_to_formula(tokens):
    """Account codes as an ``account_codes`` formula.

    ``account_dynamic_reports`` accepts a comma separated list, ranges with a
    dash (``3500-3599``) and negations. MIS writes prefixes and ranges in the
    same list, so the join is lossless.
    """
    return ','.join(tokens)


def _or_terms(terms):
    """Prefix-notation OR over a list of leaf terms.

    Odoo resolves a domain left to right; n alternatives need n-1 '|' tokens
    placed BEFORE them. Writing ['a', '|', 'b'] means "(a OR b) AND b".
    """
    if len(terms) <= 1:
        return list(terms)
    return ['|'] * (len(terms) - 1) + list(terms)


def _selector_is_domain(selector):
    """True when the selector is a list of codes; False when it is a ref."""
    return selector.strip().startswith('[')


# ----------------------------------------------------------------------
# Domain parsing
# ----------------------------------------------------------------------
def _parse_domain(text):
    """Parse a MIS domain literal into a JSON string Odoo accepts.

    MIS writes Python-ish tuples in brackets: ``[('tax_line_id.name','=','MP1')]``.
    ``ast.literal_eval`` handles it (tuples become tuples, which is fine for
    Odoo's domain parser), then ``json.dumps`` normalises it for storage.

    Returns ``(json_string, error)``.
    """
    if not text:
        return None, 'empty domain'
    try:
        parsed = ast.literal_eval(text.strip())
    except (ValueError, SyntaxError) as exc:
        return None, 'unparseable domain: %s' % exc
    if not isinstance(parsed, (list, tuple)):
        return None, 'domain is not a list'
    try:
        return json.dumps(list(parsed)), None
    except TypeError as exc:
        return None, 'domain not JSON-serialisable: %s' % exc


# ----------------------------------------------------------------------
# Top level
# ----------------------------------------------------------------------
def convert_expression(raw, kpi_code_map=None):
    """Convert one MIS expression string.

    ``kpi_code_map`` maps a MIS KPI name to the generated report line code, so
    a formula that references another KPI becomes an aggregation reference.

    Returns a :class:`Conversion`.
    """
    if raw is None:
        return Conversion(ENGINE_AGGREGATION, '', confidence=CONFIDENCE_EXACT,
                          note='no expression')
    text = str(raw).strip()
    if not text:
        return Conversion(ENGINE_AGGREGATION, '', confidence=CONFIDENCE_EXACT,
                          note='empty expression')

    # A numeric constant is a static row.
    try:
        float(text)
        return Conversion(ENGINE_DOMAIN, '[["id", "=", 0]]',
                          confidence=CONFIDENCE_REVIEW,
                          note='numeric constant %s; converted to an empty domain'
                               % text)
    except ValueError:
        pass

    # Accounting-variable form first: bal[...], crd[][...], balp[...]
    conv = _convert_accounting_variable(text)
    if conv:
        return conv

    # Aggregation: sum([A, B]) or A + B - C
    conv = _convert_aggregation(text, kpi_code_map or {})
    if conv:
        return conv

    # Nothing matched: do not guess.
    return _unparsed(text)


# MIS appends '* -1' to negate a whole expression. It is not part of the
# accounting-variable grammar, so it is stripped before matching.
NEGATE_SUFFIX_RE = re.compile(r'\s*\*\s*-\s*1\s*$')


def _convert_accounting_variable(text):
    """Handle the ``field[mode][selector][domain]`` forms."""
    negate = False
    body = text
    neg = NEGATE_SUFFIX_RE.search(body)
    if neg:
        negate = True
        body = body[:neg.start()].rstrip()

    match = MIS_ACC_RE.fullmatch(body)
    if not match:
        return None

    field = match.group('field')
    mode = match.group('mode') or ''
    account_sel = match.group('account_sel') or ''
    ml_domain = match.group('ml_domain') or ''

    # ``bal_i`` / ``bal_e``: the mode letter is glued to the field because the
    # field alternation is word-bounded. Depending on the surrounding text it
    # lands either in the field token or in account_sel as '_i'. Normalise both.
    if len(field) > 3 and field[3] in 'piseu' and field[:3] in SUPPORTED_FIELDS:
        mode = field[3]
        field = field[:3]
    elif (not mode and account_sel.startswith('_')
          and len(account_sel) == 2 and account_sel[1] in 'piseu'):
        mode = account_sel[1]
        account_sel = ml_domain
        ml_domain = ''

    if field not in SUPPORTED_FIELDS:
        return None  # fall through to aggregation / unparsed

    # mode 'p' = movement in period; 'i'/'e' = initial/end balance.
    date_scope = 'strict_range'
    if mode in ('i', 'e'):
        date_scope = 'from_beginning'

    # A leading minus on the whole expression also negates.
    zero_base = False
    if _selector_is_domain(account_sel):
        tokens = _split_account_selector(account_sel)
        if not tokens:
            # ``bal[]`` alone is an intentionally empty row in the municipal
            # chart (a placeholder heading). But ``bal[][(domain)]`` means
            # "every account, filtered by this domain" -- the empty selector
            # is not "no accounts", it is "no account restriction". SFA's own
            # VAT report uses exactly that form with tax_tag_ids, and dropping
            # the domain silently zeroed the row.
            if not ml_domain:
                return Conversion(ENGINE_AGGREGATION, '',
                                  confidence=CONFIDENCE_EXACT,
                                  note='empty account selector; row has no value')
            formula = ''
        else:
            formula = _codes_to_formula(tokens)
    else:
        zero_base = True
        formula = ''

    # A move-line domain means the account-code engine cannot express it.
    if ml_domain:
        domain_json, err = _parse_domain(ml_domain)
        if err:
            return _unparsed(text, err)
        # The account selector is still a constraint: `bal[2614][(tax...)]`
        # means "account 2614 AND this tax". Dropping it would sum every
        # account carrying the tax -- which is how box 30 became 3 750 instead
        # of 1 875 (the reverse-charge tax posts to both 2614 and 2645).
        if account_sel and _selector_is_domain(account_sel):
            codes = _split_account_selector(account_sel)
            if codes:
                account_domain = _or_terms([
                    ['account_id.code', '=like', '%s%%' % code] for code in codes
                ])
                inner = json.loads(domain_json)
                # Prefix notation: an explicit '&' applies to the next two
                # sub-expressions. Writing [acct] + inner relies on an implicit
                # AND that only happens to work when inner starts with leaves;
                # with inner starting in '|' tokens the result is wrong.
                domain_json = json.dumps(['&'] + account_domain + inner)
        confidence = CONFIDENCE_EXACT if field == 'bal' else CONFIDENCE_REVIEW
        note = ''
        if field == 'crd':
            note = ('crd selects the raw credit sum; a credit note sits on the '
                    'debit side and will not be counted')
            confidence = CONFIDENCE_REVIEW
        if field == 'deb':
            note = 'deb selects the raw debit sum'
            confidence = CONFIDENCE_REVIEW
        if field == 'pbal':
            # pbal sums only accounts whose net balance is positive. The
            # domain engine implements that as the 'positive_accounts'
            # subformula (per-account aggregation, then filter), so the value
            # is reproduced exactly rather than flagged.
            note = 'pbal: only accounts with a positive balance are summed'
            confidence = CONFIDENCE_EXACT
        if field == 'nbal':
            note = 'nbal: only accounts with a negative balance are summed'
            confidence = CONFIDENCE_EXACT
        # The domain engine sums `balance` (debit - credit).
        # - MIS `crd` is credit - debit, so its sign is flipped -> neg_sum.
        # - A trailing '* -1' negates whatever the row produced -> neg_sum.
        # `bal`/`balp` otherwise keep the balance sign -> plain sum.
        # A trailing '* -1' negates whatever the row produced, so it takes
        # precedence over the field's own aggregation. SFA's box 48 is
        # `pbal[...]*-1`: positive accounts only, then negated.
        if negate:
            subformula = 'neg_positive_accounts' if field == 'pbal' else (
                'neg_negative_accounts' if field == 'nbal' else 'neg_sum')
        elif field == 'crd':
            subformula = 'neg_sum'
        elif field == 'pbal':
            subformula = 'positive_accounts'
        elif field == 'nbal':
            subformula = 'negative_accounts'
        else:
            subformula = 'sum'
        return Conversion(ENGINE_DOMAIN, domain_json,
                          subformula=subformula,
                          date_scope=date_scope,
                          confidence=confidence, note=note)

    if zero_base:
        return _unparsed(
            text, 'account selector %r is not a code list' % account_sel)

    if negate:
        # A leading '-' makes _eval_account_codes negate the whole sum. Writing
        # '-3000,3001,3002' would negate only the first code.
        formula = '-' + formula
    if field == 'pbal':
        confidence = CONFIDENCE_REVIEW
        note = 'pbal = positive balance only; account.report sums the net balance'
    elif field == 'nbal':
        confidence = CONFIDENCE_REVIEW
        note = 'nbal = negative balance only; account.report sums the net balance'
    elif field == 'crd':
        # crd over account codes = the credit sum only. Express it as a domain
        # so the "credit only" semantics survives; account_codes would sum the
        # net balance and silently change the number.
        #
        # Odoo's domain is prefix notation: n terms need n-1 '|' tokens BEFORE
        # them. Writing ["a", "|", "b"] means "(a OR b) AND b" -- verified, it
        # silently drops a term. Build the chain explicitly.
        codes = _split_account_selector(account_sel)
        terms = [['account_id.code', '=like', '%s%%' % code] for code in codes]
        code_domain = _or_terms(terms)
        domain = code_domain + [['credit', '!=', 0]]
        return Conversion(ENGINE_DOMAIN, json.dumps(domain),
                          subformula='neg_sum',
                          date_scope=date_scope,
                          confidence=CONFIDENCE_REVIEW,
                          note='crd selects the raw credit sum only')
    else:
        confidence = CONFIDENCE_EXACT
        note = ''

    return Conversion(ENGINE_ACCOUNT_CODES, formula,
                      date_scope=date_scope,
                      confidence=confidence, note=note)


def _kpi_token_to_reference(token, kpi_code_map):
    """'KpiA' -> 'CODE.balance'. Returns None when unknown."""
    token = token.strip()
    token = re.sub(r'^_?kpi_', '', token)
    code = kpi_code_map.get(token)
    if not code:
        return None
    return '%s.balance' % code


def _convert_aggregation(text, kpi_code_map):
    """Handle ``sum([A, B])`` and ``A + B - C``.

    Returns None when the text is not an aggregation of known KPIs.
    """
    # sum([A, B, C]) * -1  -- the negated form, which appears in K2.
    m_neg = re.fullmatch(r'sum\s*\(\s*\[(.*?)\]\s*\)\s*\*\s*-\s*1', text)
    if m_neg:
        names = [n.strip() for n in m_neg.group(1).split(',') if n.strip()]
        refs = [_kpi_token_to_reference(n, kpi_code_map) for n in names]
        if all(refs):
            return Conversion(ENGINE_AGGREGATION, _negate_aggregation(' + '.join(refs)),
                              confidence=CONFIDENCE_EXACT)
        unknown = [n for n, r in zip(names, refs) if not r]
        return _unparsed(text, 'unknown KPI(s) in sum(): %s' % ', '.join(unknown))

    # sum([A, B, C])
    m = re.fullmatch(r'sum\s*\(\s*\[(.*?)\]\s*\)', text)
    if m:
        names = [n.strip() for n in m.group(1).split(',') if n.strip()]
        refs = [_kpi_token_to_reference(n, kpi_code_map) for n in names]
        if all(refs):
            return Conversion(ENGINE_AGGREGATION, ' + '.join(refs),
                              confidence=CONFIDENCE_EXACT)
        unknown = [n for n, r in zip(names, refs) if not r]
        return _unparsed(text, 'unknown KPI(s) in sum(): %s' % ', '.join(unknown))

    # A parenthesised sum negated as a whole: (A+B+C)*-1. This form exists in
    # the Swedish data (report_rr_Rorelsekostnader) and must not be refused:
    # the meaning is plain -- negate the sum of the named KPIs.
    m_neg = re.fullmatch(r'\((\s*[A-Za-z_][\w]*(\s*[+\-]\s*[A-Za-z_][\w]*)*\s*)\)'
                         r'\s*\*\s*-\s*1', text)
    if m_neg:
        inner = _convert_aggregation(m_neg.group(1), kpi_code_map)
        if inner and inner.engine == ENGINE_AGGREGATION and inner.formula:
            # The aggregation engine parses terms split on +/-, with no
            # parentheses, so distribute the negation instead of emitting
            # '-(A + B)': -(A + B) == -A - B.
            distributed = _negate_aggregation(inner.formula)
            return Conversion(ENGINE_AGGREGATION, distributed,
                              confidence=CONFIDENCE_EXACT)
        return inner or _unparsed(text, 'unparseable negated sum')

    # Bare arithmetic on KPI names: A + B - C. Only + and - are seen in the
    # Swedish data (measured); anything else falls through to unparsed so we
    # never invent precedence rules MIS did not use.
    if not re.fullmatch(r'[A-Za-z_][\w]*(\s*[+\-]\s*[A-Za-z_][\w]*)+', text):
        return None
    parts = re.split(r'\s*([+\-])\s*', text)
    refs = []
    unknown = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part in ('+', '-'):
            refs.append(part)
            continue
        ref = _kpi_token_to_reference(part, kpi_code_map)
        if ref:
            refs.append(ref)
        else:
            unknown.append(part)
    if unknown:
        return _unparsed(text, 'unknown KPI(s): %s' % ', '.join(unknown))
    if not refs:
        return None
    return Conversion(ENGINE_AGGREGATION, ' '.join(refs),
                      confidence=CONFIDENCE_EXACT)


def _negate_aggregation(formula):
    """Flip every sign in an aggregation formula.

    'A.balance + B.balance - C.balance' -> '-A.balance - B.balance + C.balance'
    The aggregation engine splits on +/- and applies each operator, so a
    leading '-' on the first term is enough to negate the whole sum.
    """
    tokens = re.split(r'\s*([+\-])\s*', formula)
    out = []
    sign = -1  # the whole expression is negated
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if token in ('+', '-'):
            sign = -1 if token == '+' else 1
            continue
        out.append(('-' if sign < 0 else '+') + token)
    if not out:
        return formula
    # Drop a leading '+' for readability; keep a leading '-'.
    first = out[0]
    return (first if first.startswith('-') else first[1:]) + ''.join(out[1:])


def _unparsed(text, reason='no known pattern'):
    """The refusal path: keep the text, warn, never guess."""
    return Conversion(
        ENGINE_DOMAIN,
        json.dumps([['id', '=', 0]]),
        confidence=CONFIDENCE_UNPARSED,
        note='UNCONVERTED: %r (%s)' % (text, reason),
    )


def convert_style(style):
    """Translate a ``mis.report.style`` into line/column hints.

    Styles in the Swedish data affect boldness, colour and number format. Only
    the pieces ``account.report`` has a concept for are translated; the rest is
    reported so it can be recreated by hand if it turns out to matter.
    """
    if not style:
        return {}
    hints = {}
    for attr in ('font_style', 'font_weight', 'color', 'background_color',
                 'indent_level', 'hide_empty', 'hide_always'):
        value = getattr(style, attr, None)
        if value not in (None, False, '', 0):
            hints[attr] = value
    return hints
