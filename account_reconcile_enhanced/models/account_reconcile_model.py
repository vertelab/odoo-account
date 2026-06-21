# Copyright 2026 - Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.tools import SQL


class AccountReconcileModel(models.Model):
    _inherit = "account.reconcile.model"

    created_automatically = fields.Boolean(
        default=False,
        copy=False,
        help="Technical field to know if the rule was created automatically or by a user.",
    )
    next_activity_type_id = fields.Many2one(
        comodel_name="mail.activity.type",
        string="Next Activity",
        help="If set, an activity of this type will be scheduled on the "
        "journal entry after the reconciliation model is applied.",
    )
    can_be_proposed = fields.Boolean(
        compute="_compute_can_be_proposed",
        store=True,
        help="Technical field: True if this model can be proposed for auto-matching.",
    )
    is_fee_model = fields.Boolean(
        string="Bank Fee Model",
        default=False,
        help="Mark this reconciliation model as a bank fee model. "
        "Fee models are automatically applied when a small residual "
        "remains on a deposit statement line after partial matching, "
        "indicating bank charges were deducted.",
    )
    fee_threshold = fields.Float(
        string="Fee Threshold (%)",
        default=3.0,
        help="Maximum fee percentage of the original deposit amount. "
        "The fee model triggers when the residual on an incoming "
        "statement line is less than this percentage of the original amount. "
        "Example: With 3% threshold, a $100 deposit with ≤ $2.91 residual "
        "will trigger the fee model.",
    )

    @api.depends("rule_type", "active")
    def _compute_can_be_proposed(self):
        for rec in self:
            rec.can_be_proposed = rec.rule_type in (
                "invoice_matching",
                "writeoff_suggestion",
            ) and rec.active

    @api.model
    def get_available_reconcile_model_per_statement_line(self, statement_line_ids):
        """Return available reconciliation models for each statement line.
        Uses optimized SQL query for performance.

        :param statement_line_ids: list of bank statement line IDs
        :return: dict mapping statement_line_id -> list of {'id', 'display_name'}
        """
        self.check_access("read")
        self.env["account.reconcile.model"].flush_model()
        self.env["account.bank.statement.line"].flush_model()
        self.env.cr.execute(
            SQL(
                """
            WITH matching_journal_ids AS (
                    SELECT account_reconcile_model_id,
                           ARRAY_AGG(account_journal_id) AS ids
                      FROM account_journal_account_reconcile_model_rel
                  GROUP BY account_reconcile_model_id
                 ),
                 matching_partner_ids AS (
                    SELECT account_reconcile_model_id,
                           ARRAY_AGG(res_partner_id) AS ids
                      FROM account_reconcile_model_res_partner_rel
                  GROUP BY account_reconcile_model_id
                 )

          SELECT st_line.id AS st_line_id,
                 array_agg(reco_model.id ORDER BY reco_model.sequence ASC, reco_model.id ASC) AS reco_model_ids,
                 array_agg(COALESCE(reco_model.name -> %(lang)s, reco_model.name -> 'en_US') ORDER BY reco_model.sequence ASC, reco_model.id ASC) AS reco_model_names
            FROM account_bank_statement_line st_line
       LEFT JOIN LATERAL (
                   SELECT DISTINCT reco_model.id,
                          reco_model.sequence
                     FROM account_reconcile_model reco_model
                LEFT JOIN matching_journal_ids ON reco_model.id = matching_journal_ids.account_reconcile_model_id
                LEFT JOIN matching_partner_ids ON reco_model.id = matching_partner_ids.account_reconcile_model_id
                LEFT JOIN account_reconcile_model_line reco_model_line ON reco_model_line.model_id = reco_model.id
                    WHERE (matching_journal_ids.ids IS NULL OR st_line.journal_id = ANY(matching_journal_ids.ids))
                      AND (matching_partner_ids.ids IS NULL OR st_line.partner_id = ANY(matching_partner_ids.ids))
                      AND (
                          CASE COALESCE(reco_model.match_amount, '')
                              WHEN 'lower' THEN st_line.amount <= reco_model.match_amount_max
                              WHEN 'greater' THEN st_line.amount >= reco_model.match_amount_min
                              WHEN 'between' THEN
                                  (st_line.amount BETWEEN reco_model.match_amount_min AND reco_model.match_amount_max) OR
                                  (st_line.amount BETWEEN reco_model.match_amount_max AND reco_model.match_amount_min)
                              ELSE TRUE
                          END
                          )
                      AND (
                              reco_model.match_label IS NULL
                              OR (
                                  reco_model.match_label = 'contains'
                                   AND (
                                      st_line.payment_ref ILIKE '%%' || reco_model.match_label_param || '%%'
                                      OR st_line.transaction_details::TEXT ILIKE '%%' || reco_model.match_label_param || '%%'
                                   )
                              ) OR (
                                  reco_model.match_label = 'not_contains'
                                  AND NOT (
                                      st_line.payment_ref ILIKE '%%' || reco_model.match_label_param || '%%'
                                      OR st_line.transaction_details::TEXT ILIKE '%%' || reco_model.match_label_param || '%%'
                                   )
                              ) OR (
                                  reco_model.match_label = 'match_regex'
                                  AND (
                                      st_line.payment_ref ~* reco_model.match_label_param
                                      OR st_line.transaction_details::TEXT ~* reco_model.match_label_param
                                   )
                              )
                          )
                      AND reco_model.company_id = st_line.company_id
                      AND reco_model.trigger = 'manual'
                      AND reco_model_line.account_id IS NOT NULL
                 ) AS reco_model ON TRUE
           WHERE st_line.id IN %(statement_lines)s
             AND reco_model.id IS NOT NULL
           GROUP BY st_line.id
            """,
                lang=self.env.lang,
                statement_lines=tuple(statement_line_ids),
            )
        )
        query_result = self.env.cr.fetchall()
        return {
            st_line_id: [
                {"id": model_id, "display_name": model_name}
                for model_id, model_name in zip(model_ids, model_names)
            ]
            for st_line_id, model_ids, model_names in query_result
        }

    def _apply_reconcile_models(self, statement_lines):
        """Apply matching reconciliation models to unreconciled statement lines.

        Uses SQL-optimized query with two-phase matching:
        1. Regular reconciliation models (trigger = manual, can_be_proposed)
        2. Bank fee models (is_fee_model = True) as fallback when a small
           residual remains on incoming deposits — indicating bank charges.
        """
        if not self or not statement_lines:
            return
        self.env["account.reconcile.model"].flush_model()
        statement_lines.flush_recordset(
            [
                "journal_id",
                "amount",
                "amount_residual",
                "transaction_details",
                "payment_ref",
                "partner_id",
                "company_id",
                "move_id",
            ]
        )
        self.env.cr.execute(
            SQL(
                """
            WITH matching_journal_ids AS (
                    SELECT account_reconcile_model_id,
                           ARRAY_AGG(account_journal_id) AS ids
                      FROM account_journal_account_reconcile_model_rel
                  GROUP BY account_reconcile_model_id
                 ),
                 matching_partner_ids AS (
                    SELECT account_reconcile_model_id,
                           ARRAY_AGG(res_partner_id) AS ids
                      FROM account_reconcile_model_res_partner_rel
                  GROUP BY account_reconcile_model_id
                 ),
                 model_fees AS (
                    SELECT model_fees.id,
                           model_fees.fee_threshold,
                           matching_journal_ids.ids AS journal_ids
                      FROM account_reconcile_model model_fees
                      JOIN account_reconcile_model_line model_lines
                        ON model_lines.model_id = model_fees.id
                 LEFT JOIN matching_journal_ids
                        ON model_fees.id = matching_journal_ids.account_reconcile_model_id
                     WHERE model_fees.is_fee_model IS TRUE
                       AND model_fees.active IS TRUE
                       AND model_fees.id IN %s
                       AND model_lines.account_id IS NOT NULL
                 )

          SELECT st_line.id AS st_line_id,
                 COALESCE(reco_model.id, model_fees.id) AS reco_model_id
            FROM account_bank_statement_line st_line
            JOIN account_move move ON st_line.move_id = move.id
       LEFT JOIN LATERAL (
                   SELECT reco_model.id
                     FROM account_reconcile_model reco_model
                LEFT JOIN matching_journal_ids ON reco_model.id = matching_journal_ids.account_reconcile_model_id
                LEFT JOIN matching_partner_ids ON reco_model.id = matching_partner_ids.account_reconcile_model_id
                    WHERE (matching_journal_ids.ids IS NULL OR st_line.journal_id = ANY(matching_journal_ids.ids))
                      AND (matching_partner_ids.ids IS NULL OR st_line.partner_id = ANY(matching_partner_ids.ids))
                      AND (
                              CASE COALESCE(reco_model.match_amount, '')
                                  WHEN 'lower' THEN st_line.amount <= reco_model.match_amount_max
                                  WHEN 'greater' THEN st_line.amount >= reco_model.match_amount_min
                                  WHEN 'between' THEN
                                      (st_line.amount BETWEEN reco_model.match_amount_min AND reco_model.match_amount_max) OR
                                      (st_line.amount BETWEEN reco_model.match_amount_max AND reco_model.match_amount_min)
                                  ELSE TRUE
                              END
                          )
                      AND (
                              reco_model.match_label IS NULL
                              OR (
                                  reco_model.match_label = 'contains'
                                   AND (
                                      st_line.payment_ref ILIKE '%%' || reco_model.match_label_param || '%%'
                                      OR st_line.transaction_details::TEXT ILIKE '%%' || reco_model.match_label_param || '%%'
                                      OR move.narration::TEXT ILIKE '%%' || reco_model.match_label_param || '%%'
                                   )
                              ) OR (
                                  reco_model.match_label = 'not_contains'
                                  AND NOT (
                                      st_line.payment_ref ILIKE '%%' || reco_model.match_label_param || '%%'
                                      OR st_line.transaction_details::TEXT ILIKE '%%' || reco_model.match_label_param || '%%'
                                      OR move.narration::TEXT ILIKE '%%' || reco_model.match_label_param || '%%'
                                   )
                              ) OR (
                                  reco_model.match_label = 'match_regex'
                                  AND (
                                      st_line.payment_ref ~* reco_model.match_label_param
                                      OR st_line.transaction_details::TEXT ~* reco_model.match_label_param
                                      OR move.narration::TEXT ~* reco_model.match_label_param
                                   )
                              )
                          )
                      AND reco_model.is_fee_model IS FALSE
                      AND reco_model.id IN %s
                      AND reco_model.can_be_proposed IS TRUE
                      AND reco_model.company_id = st_line.company_id
                 ORDER BY reco_model.sequence ASC, reco_model.id ASC
                    LIMIT 1
                 ) AS reco_model ON TRUE
       LEFT JOIN LATERAL (
                   SELECT model_fees.id
                     FROM model_fees
                    WHERE (model_fees.journal_ids IS NULL
                           OR st_line.journal_id = ANY(model_fees.journal_ids))
                      AND SIGN(st_line.amount) > 0
                      AND SIGN(st_line.amount_residual) > 0
                      AND ABS(st_line.amount_residual) <
                          (model_fees.fee_threshold / 100.0) * st_line.amount
                          / (1.0 + model_fees.fee_threshold / 100.0)
                    LIMIT 1
                 ) AS model_fees ON TRUE
           WHERE st_line.id IN %s
        """,
                tuple(self.ids),
                tuple(self.ids),
                tuple(statement_lines.ids),
            )
        )

        query_result = self.env.cr.fetchall()
        processed_st_line_ids = set()

        for st_line_id, reco_model_id in query_result:
            if st_line_id in processed_st_line_ids or reco_model_id is None:
                continue

            st_line = (
                self.env["account.bank.statement.line"]
                .browse(st_line_id)
                .with_prefetch(statement_lines.ids)
            )
            reco_model = (
                self.env["account.reconcile.model"]
                .browse(reco_model_id)
                .with_prefetch(self.ids)
            )
            reco_model.with_user(SUPERUSER_ID)._trigger_reconciliation_model(st_line)
            processed_st_line_ids.add(st_line_id)

    def _trigger_reconciliation_model(self, statement_line):
        """Apply this reconciliation model to a statement line, creating
        counterpart journal items and reconciling.
        """
        self.ensure_one()
        liquidity_line, suspense_line, other_lines = statement_line._seek_for_lines()

        amls_to_create = list(
            self._apply_lines_for_bank_widget(
                residual_amount_currency=sum(
                    suspense_line.mapped("amount_currency")
                ),
                partner=statement_line.partner_id,
                st_line=statement_line,
            )
        )

        statement_line.with_user(SUPERUSER_ID)._set_move_line_to_statement_line_move(
            liquidity_line + other_lines, amls_to_create
        )
        if any(aml.get("tax_ids") for aml in amls_to_create):
            statement_line._recompute_tax_lines()
        if self.next_activity_type_id:
            statement_line.move_id.activity_schedule(
                activity_type_id=self.next_activity_type_id.id,
                user_id=self.env.user.id,
            )
        statement_line.move_id._message_log(
            author_id=self.env.user.partner_id.id,
            body=_("Reconciliation model %s applied", self.name),
        )

    def trigger_reconciliation_model(self, statement_line_id):
        """Action to manually trigger a reconciliation model on a statement line."""
        self.ensure_one()
        statement_line = self.env["account.bank.statement.line"].browse(
            statement_line_id
        ).exists()
        self._trigger_reconciliation_model(statement_line)

    def write(self, vals):
        res = super().write(vals)
        unreconciled_statement_lines = self.env[
            "account.bank.statement.line"
        ].search(
            [
                *self._check_company_domain(self.env.company),
                ("is_reconciled", "=", False),
            ]
        )
        if unreconciled_statement_lines:
            unreconciled_statement_lines.line_ids.filtered(
                lambda line: line.account_id
                == line.move_id.journal_id.suspense_account_id
                and line.reconcile_model_id in self
            ).reconcile_model_id = False
            self._apply_reconcile_models(unreconciled_statement_lines)

        return res

    @api.model_create_multi
    def create(self, vals_list):
        reco_models = super().create(vals_list)
        unreconciled_statement_lines = self.env[
            "account.bank.statement.line"
        ].search(
            [
                *self._check_company_domain(self.env.company),
                ("is_reconciled", "=", False),
            ]
        )
        if unreconciled_statement_lines:
            reco_models._apply_reconcile_models(unreconciled_statement_lines)
        return reco_models

    def action_archive(self):
        res = super().action_archive()
        unreconciled_statement_lines = self.env[
            "account.bank.statement.line"
        ].search(
            [
                *self._check_company_domain(self.env.company),
                ("is_reconciled", "=", False),
                ("line_ids.reconcile_model_id", "in", self.ids),
            ]
        )
        if unreconciled_statement_lines:
            unreconciled_statement_lines.line_ids.filtered(
                lambda line: line.account_id
                == line.move_id.journal_id.suspense_account_id
            ).reconcile_model_id = False
        return res
