/** @odoo-module **/

/**
 * account_reconcile_oca_ux_fix — T/11503
 *
 * Keep the search filter in the Reconcile tab after a visit to the
 * Manual operation tab.
 *
 * ROOT CAUSE (measured in the browser 2026-09-28, sfa-test):
 *
 *   Switching notebook tabs does NOT touch the search model. What happens is
 *   that the selected record changes, and the new record's form view carries
 *   its own `search_default_partner_id` in the action context, which
 *   overwrites the filter the user had set.
 *
 *   The chain:
 *     1. reconcile_form_controller.esm.js: on a tab switch the form reloads
 *        and calls `this.env.parentController.selectRecord()` — with NO
 *        argument.
 *     2. reconcile_controller.esm.js `selectRecord(record)`: with `record`
 *        undefined it falls through to
 *        `resId = this.getRecordIdToSelect(candidates)`.
 *     3. `getRecordIdToSelect()` deliberately picks the NEXT record when the
 *        previously selected one is no longer in the list:
 *
 *            "The record is not displayed anymore (e.g. the unreconciled
 *             filter is set), so its former position is now held by the
 *             record that followed it."
 *
 *     4. The newly selected record belongs to a different partner, and its
 *        form view declares
 *            context="{'search_default_partner_id': partner_id, ...}"
 *        (account_reconcile_oca/views/account_bank_statement_line.xml), which
 *        installs a NEW partner filter and discards the previous one.
 *
 *   Measured effect: filter chips went from
 *     [Not Reconciled, Partner NAVINORDIC]  ->  [Partner NAVINORDIC]
 *     ->  [Partner T & A VVS AB]  ->  []
 *   while the record count went 2 -> 61 -> 80.
 *
 * WHY THE PREVIOUS PATCH DID NOT WORK:
 *   It exported `searchModel` through `getLocalState`. But `searchModel` is
 *   already exported as GLOBAL state by WithSearch
 *   (web/static/src/search/with_search/with_search.js), so adding it locally
 *   changes nothing. The filter is lost because the RECORD CHANGES, not
 *   because the search model is not persisted.
 *
 * THE FIX:
 *   When the parent controller is asked to re-select a record after a form
 *   reload, and the previously selected record is still available, keep it.
 *   That way the record does not change, no new `search_default_partner_id`
 *   is applied, and the user's filter survives the tab switch.
 *
 *   Implemented with `patch()` so the OCA sources stay untouched and the fix
 *   survives OCA updates.
 *
 * VERIFICATION:
 *   Set a partner filter in the Reconcile tab, switch to Manual operation and
 *   back. The filter must still be there and the record must not change.
 */

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const reconcileView = registry.category("views").get("reconcile");

if (reconcileView && reconcileView.Controller) {
    patch(reconcileView.Controller.prototype, {
        /**
         * Keep the currently selected record when the controller is asked to
         * re-select without an explicit record.
         *
         * `reloadFormController()` calls `selectRecord()` with no argument
         * after every tab switch. Without this override that call falls
         * through to `getRecordIdToSelect()`, which advances to the next
         * record and thereby replaces the user's search filter.
         */
        async selectRecord(record) {
            if (record === undefined && this.state.selectedRecordId) {
                const stillThere = this.model.root.records.some(
                    (modelRecord) => modelRecord.resId === this.state.selectedRecordId
                );
                if (stillThere) {
                    // Re-select the same record: no record change, no new
                    // search_default_partner_id, filter preserved.
                    return super.selectRecord(
                        this.model.root.records.find(
                            (modelRecord) =>
                                modelRecord.resId === this.state.selectedRecordId
                        )
                    );
                }
            }
            return super.selectRecord(...arguments);
        },
    });
}
