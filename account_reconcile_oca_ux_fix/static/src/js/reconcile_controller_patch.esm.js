/** @odoo-module **/

/**
 * account_reconcile_oca_ux_fix — T/11503
 *
 * Behåll kundfiltret i fliken Reconcile efter besök i Manual operation.
 *
 * ROTORSAK (belagd i källkoden 2026-09-16):
 *   OCA:s ReconcileController (account_reconcile_oca) registrerar en egen
 *   useSetupAction({getLocalState}) som BARA exporterar selectedRecordId.
 *   Föräldern KanbanController exporterar modelState, och sökfiltret bor i
 *   searchModel som WithSearch exporterar som GLOBAL state.
 *
 *   Kedjan:
 *     1. with_search.js rad 72-76: getGlobalState -> searchModel (global)
 *     2. action_service.js rad 971-977: Object.assign(...exportFns.map(fn => fn()))
 *     3. reconcile_controller.esm.js rad 18-24: getLocalState -> BARA selectedRecordId
 *     4. reconcile_form_controller.esm.js rad 22-33: reloadFormController()
 *        -> model.root.load() + render(true) UTAN att filtret appliceras igen
 *
 * FIX:
 *   Utöka getLocalState att även exportera searchModel, så filtret bevaras.
 *   Implementerad som patch() — OCA:s källkod redigeras inte, så fixen
 *   överlever OCA-uppdateringar.
 *
 * Verifiering:
 *   Sätt ett kundfilter i Reconcile-fliken -> byt till Manual operation ->
 *   byt tillbaka. Filtret ska vara kvar.
 */

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const reconcileView = registry.category("views").get("reconcile");

if (reconcileView && reconcileView.Controller) {
    patch(reconcileView.Controller.prototype, {
        /**
         * Utöka den lokala staten med sökmodellen så att kundfiltret
         * överlever flikbytet Reconcile <-> Manual operation.
         */
        getLocalState() {
            const state = super.getLocalState(...arguments) || {};
            const searchModel = this.env.searchModel;
            if (searchModel && typeof searchModel.exportState === "function") {
                state.searchModel = JSON.stringify(searchModel.exportState());
            }
            return state;
        },
    });
}
