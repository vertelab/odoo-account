/** Copyright 2026 Vertel AB
 *  SPDX-License-Identifier: AGPL-3
 *
 *  Systray "pen": shows how many vendor bills are waiting for the
 *  current user's approval. Clicking it opens the filtered bill list.
 */
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class BillApprovalSystray extends Component {
    static template = "account_bill_approval.BillApprovalSystray";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ count: 0 });

        onWillStart(async () => {
            await this._fetchCount();
        });
    }

    async _fetchCount() {
        try {
            this.state.count = await this.orm.call(
                "bill.approval.user.line",
                "ret_bill_approval_count",
                []
            );
        } catch {
            // The user may lack access to the model — hide the counter.
            this.state.count = 0;
        }
    }

    async onClick() {
        await this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("Bills Waiting For My Approval"),
                res_model: "account.move",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                domain: [["to_approve", "=", true]],
                context: { search_default_filter_my_approval: 1 },
                target: "current",
            },
            { clearBreadcrumbs: true }
        );
    }
}

export const billApprovalSystrayItem = {
    Component: BillApprovalSystray,
};

registry.category("systray").add(
    "account_bill_approval.BillApprovalSystray",
    billApprovalSystrayItem,
    { sequence: 98 }
);
