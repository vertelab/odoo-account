/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useBus } from "@web/core/utils/hooks";

class AccountDynamicReport extends Component {
    static template = "account_dynamic_reports.AccountDynamicReport";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.rpc = useService("rpc");
        
        this.state = useState({
            reportName: "",
            lines: [],
            columns: [],
            expandedLines: new Set(),
            isLoading: true,
            error: null,
            options: {
                date: {
                    date_from: null,
                    date_to: null,
                },
                comparison: false,
            },
        });
        
        onWillStart(async () => {
            await this.loadReport();
        });
    }

    async loadReport() {
        const context = this.props.context || {};
        const reportId = context.report_id;
        
        if (!reportId) {
            this.state.error = "No report ID in context";
            this.state.isLoading = false;
            return;
        }

        try {
            // Get report metadata
            const report = await this.orm.read("account.report", [reportId], ["name"]);
            if (report.length > 0) {
                this.state.reportName = report[0].name;
            }

            // Get report lines and columns via custom RPC
            const result = await this.rpc("/account_dynamic_report/get_lines", {
                report_id: reportId,
                options: this.state.options,
            });

            if (result.error) {
                this.state.error = result.error;
            } else {
                this.state.lines = result.lines || [];
                this.state.columns = result.columns || [];
                // Auto-expand top-level lines
                for (const line of this.state.lines) {
                    if (line.unfoldable && line.unfolded) {
                        this.state.expandedLines.add(line.id);
                    }
                }
            }
        } catch (e) {
            this.state.error = e.message || String(e);
        } finally {
            this.state.isLoading = false;
        }
    }

    toggleLine(lineId) {
        if (this.state.expandedLines.has(lineId)) {
            this.state.expandedLines.delete(lineId);
        } else {
            this.state.expandedLines.add(lineId);
        }
    }

    isExpanded(lineId) {
        return this.state.expandedLines.has(lineId);
    }

    getVisibleLines() {
        const visible = [];
        const addLineAndDescendants = (lineId) => {
            const line = this.state.lines.find(l => l.id === lineId);
            if (!line) return;
            visible.push(line);
            if (this.isExpanded(lineId)) {
                const children = this.state.lines.filter(l => l.parent_id === lineId);
                for (const child of children) {
                    addLineAndDescendants(child.id);
                }
            }
        };

        const roots = this.state.lines.filter(l => !l.parent_id);
        for (const root of roots) {
            addLineAndDescendants(root.id);
        }
        return visible;
    }

    getIndentStyle(level) {
        const indent = (level - 1) * 20;
        return `padding-left: ${indent}px`;
    }

    getLineClass(line) {
        const classes = ["o_dynamic_report_line"];
        if (line.unfoldable) {
            classes.push("o_dynamic_report_unfoldable");
        }
        if (line.level === 1) {
            classes.push("o_dynamic_report_section_primary");
        }
        if (line.level >= 4 && line.level <= 6) {
            classes.push("o_dynamic_report_section_secondary");
        }
        return classes.join(" ");
    }

    getExpandIcon(line) {
        if (!line.unfoldable) return "";
        return this.isExpanded(line.id) ? "▼" : "▶";
    }

    async onDateChange() {
        this.state.isLoading = true;
        await this.loadReport();
    }
}

AccountDynamicReport.template = "account_dynamic_reports.AccountDynamicReport";

registry.category("actions").add("account_dynamic_report", AccountDynamicReport);

export default AccountDynamicReport;
