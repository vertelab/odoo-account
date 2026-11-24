/** @odoo-module **/

import { Component } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { deserializeDate, serializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

/**
 * A labelled date field with a help text.
 *
 * Odoo's own ``DateTimeInput`` renders nothing but the ``<input>``: the label
 * and the explanation belong to the surrounding form. This component supplies
 * both, so every date in the report gets the same structure and the same
 * translatable strings -- and so the user can see *what the date actually
 * means*, which is the whole point when one report cuts off open items and
 * another converts at a rate.
 *
 * ``value`` is the server-side string (``YYYY-MM-DD``) or ``null``; the
 * component converts to and from luxon internally so the parent never has to
 * deal with two date representations.
 */
export class DateField extends Component {
    static template = "account_dynamic_reports.DateField";
    static components = { DateTimeInput };

    static props = {
        id: { type: String, optional: true },
        label: { type: String },
        help: { type: String, optional: true },
        value: { type: [String, { value: null }], optional: true },
        onChange: { type: Function },
        /** Shows an "(optional)" hint next to the label when false. */
        required: { type: Boolean, optional: true },
    };

    static defaultProps = {
        required: false,
    };

    get dateValue() {
        const raw = this.props.value;
        if (!raw) {
            return false;
        }
        try {
            return deserializeDate(raw);
        } catch {
            // A malformed value must not break the whole report: show an empty
            // field and let the user pick a date again.
            return false;
        }
    }

    onApply(value) {
        const serialized = value ? serializeDate(value) : null;
        this.props.onChange(serialized);
    }

    /** The id the label points at, so the field is reachable by screen readers. */
    get inputId() {
        return this.props.id || `o_dynamic_report_date_${this.props.label.toLowerCase().replace(/\s+/g, "_")}`;
    }

    get helpId() {
        return `${this.inputId}_help`;
    }

    get optionalLabel() {
        return _t("(optional)");
    }
}
