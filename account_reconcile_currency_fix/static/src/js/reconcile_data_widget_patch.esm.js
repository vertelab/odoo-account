/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { getCurrency } from "@web/core/currency";
import { formatDate, parseDate } from "@web/core/l10n/dates";
import { floatIsZero } from "@web/core/utils/numbers";
import { formatMonetary } from "@web/views/fields/formatters";

const fieldRegistry = registry.category("fields");
const widgetField = fieldRegistry.get("account_reconcile_oca_data");
if (widgetField) {
    patch(widgetField.component.prototype, {
        getReconcileLines() {
            var data = this.props.record.data[this.props.name].data;
            const totals = { debit: 0, credit: 0 };
            if (!data || !data.length) {
                return { lines: [], totals };
            }
            for (var line in data) {
                data[line].amount_format = formatMonetary(data[line].amount, {
                    currencyId: data[line].currency_id,
                });
                data[line].debit_format = formatMonetary(data[line].debit, {
                    currencyId: data[line].currency_id,
                });
                data[line].credit_format = formatMonetary(data[line].credit, {
                    currencyId: data[line].currency_id,
                });
                data[line].amount_currency_format = formatMonetary(
                    data[line].currency_amount,
                    { currencyId: data[line].line_currency_id }
                );
                if (data[line].original_amount) {
                    data[line].original_amount_format = formatMonetary(
                        data[line].original_amount,
                        { currencyId: data[line].currency_id }
                    );
                }
                data[line].date_format = formatDate(
                    parseDate(data[line].date, undefined, { isUTC: true })
                );
                totals.debit += data[line].debit || 0;
                totals.credit += data[line].credit || 0;
            }
            totals.balance = totals.debit - totals.credit;
            const [firstLine = {}] = Object.values(data);
            const currency = getCurrency(firstLine.currency_id);
            const decimals = currency ? currency.digits[1] : 2;
            const hasOpenBalance = !floatIsZero(totals.balance, decimals);
            const absoluteBalance = Math.abs(totals.balance);
            const openDebitFmt =
                totals.balance < 0 ? formatMonetary(absoluteBalance, { currency }) : null;
            const openCreditFmt =
                totals.balance > 0 ? formatMonetary(absoluteBalance, { currency }) : null;
            return { lines: data, hasOpenBalance, openDebitFmt, openCreditFmt };
        },
    });
}
