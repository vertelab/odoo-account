/** @odoo-module **/
/**
 * Client-side sorting + partner click handler for Aged Partner Balance report.
 * - Column headers sort the table asc/desc
 * - Partner names open customer invoices filtered to the report's criteria
 */

var sortState = {};

function setupTableSorting() {
    document.querySelectorAll('.data_table').forEach(function(table) {
        var headers = table.querySelectorAll('.act_as_thead .act_as_cell');
        var tableId = 't_' + Math.random().toString(36).substr(2, 9);
        sortState[tableId] = { colIndex: -1, direction: 'asc' };
        table.dataset.sortTable = tableId;

        headers.forEach(function(header, colIdx) {
            header.style.cursor = 'pointer';
            header.title = 'Klicka f\u00f6r att sortera';
            header.addEventListener('click', function onClickHeader() {
                var state = sortState[table.dataset.sortTable];
                var rows = Array.from(table.querySelectorAll('.act_as_row.lines'));
                if (!rows.length) return;

                if (state.colIndex === colIdx) {
                    state.direction = (state.direction === 'asc') ? 'desc' : 'asc';
                } else {
                    state.colIndex = colIdx;
                    state.direction = 'asc';
                }

                headers.forEach(function(h) {
                    h.textContent = h.textContent.replace(/\s*[\u25B2\u25BC]$/, '');
                });

                rows.sort(function(a, b) {
                    var aCell = a.querySelectorAll('.act_as_cell')[colIdx];
                    var bCell = b.querySelectorAll('.act_as_cell')[colIdx];
                    if (!aCell || !bCell) return 0;

                    var aVal = aCell.textContent.trim();
                    var bVal = bCell.textContent.trim();
                    var isMonetary = /\d[\d\s]*,\d{2}\s+[A-Z]{3}/.test(aVal);

                    if (isMonetary) {
                        var parseMoney = function(s) {
                            return parseFloat((s || '0').replace(/[^\d,\-]/g, '').replace(',', '.')) || 0;
                        };
                        aVal = parseMoney(aVal);
                        bVal = parseMoney(bVal);
                    } else {
                        aVal = (aVal || '').toLowerCase();
                        bVal = (bVal || '').toLowerCase();
                    }

                    if (aVal < bVal) return state.direction === 'asc' ? -1 : 1;
                    if (aVal > bVal) return state.direction === 'asc' ? 1 : -1;
                    return 0;
                });

                var tbody = rows[0].parentNode;
                rows.forEach(function(row) { tbody.appendChild(row); });
                headers[colIdx].textContent += state.direction === 'asc' ? ' \u25B2' : ' \u25BC';
            });
        });
    });

    // Partner name click handler: open customer invoices
    document.querySelectorAll('.partner_clickable').forEach(function(span) {
        span.style.cursor = 'pointer';
        span.style.color = '#0066cc';
        span.addEventListener('click', function(ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var domain = span.getAttribute('data-partner-domain');
            if (!domain) return;
            try {
                var parsed = JSON.parse(domain);
                // Extract partner_id from the domain
                var partnerId = 0;
                for (var i = 0; i < parsed.length; i++) {
                    if (parsed[i][0] === 'partner_id' && parsed[i][1] === '=') {
                        partnerId = parsed[i][2];
                        break;
                    }
                }
                // Navigate to customer invoices filtered by partner
                var url = '/odoo/customer-invoices/0/res.partner/' + partnerId + '/invoicing';
                if (window.parent) {
                    window.parent.location.href = url;
                } else {
                    window.location.href = url;
                }
            } catch(e) {
                // ignore
            }
        });
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupTableSorting);
} else {
    setupTableSorting();
}
