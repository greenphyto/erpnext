# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import erpnext
from frappe.utils import flt

def execute(filters=None):
    return Report(filters).execute()


class Report:
    def __init__(self, filters):
        self.filters = filters or {}
        self.company = self.filters.get("company") or erpnext.get_default_company()
        self.columns = []
        self.data = []
        self.company_currency = frappe.get_cached_value("Company", self.company, "default_currency")

    def setup_condition(self):
        # Dynamic WHERE fragments driven by filters
        self.cond = ""
        if self.filters.get("work_order"):
            self.cond += " AND se.work_order = %(work_order)s"
        if self.filters.get("operation"):
            self.cond += " AND se.operation = %(operation)s"
        if self.filters.get("item_code"):
            self.cond += " AND wo.production_item = %(item_code)s"

    def setup_column(self):
        self.columns = [
            {"fieldname": "account", "label": "WIP Account", "fieldtype": "Link", "options": "Account", "width": 240},
            {"fieldname": "work_order", "label": "Work Order ID", "fieldtype": "Link", "options": "Work Order", "width": 160},
            {"fieldname": "produced_item", "label": "Produced Item", "fieldtype": "Link", "options": "Item", "width": 160},
            {"fieldname": "product_name", "label": "Product Name", "fieldtype": "Data", "width": 200},
            {"fieldname": "qty", "label": "Qty (KG)", "fieldtype": "Float", "width": 100},
            {"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "options": "currency", "width": 120},
            {"fieldname": "map_price", "label": "MAP Price", "fieldtype": "Currency", "options": "map_currency", "width": 120},
            # hidden helpers to drive currency columns
            {"fieldname": "currency", "label": "Currency", "fieldtype": "Data", "hidden": 1},
            {"fieldname": "map_currency", "label": "MAP Currency", "fieldtype": "Data", "hidden": 1},
        ]

    def get_wip_accounts(self):
        accounts = [
            d.wip_account
            for d in frappe.get_all(
                "Operation WIP Account",
                filters={
                    "parent": self.company,
                    "parenttype": "Company",
                    "parentfield": "operation_wip_account",
                    "operation":['!=', 'Harvesting']
                },
                fields=["wip_account"],
            )
            if d.wip_account
        ]
        return accounts
    
    def get_item_price_map(self, source="Item Price"):
        # get all item
        # get convert to uom
        # 3 source: Item price, Sales Invoice, Valuation Rate
        price_map = {}
        if source == "Item Price":
            data = frappe.db.sql("""
                SELECT 
                    ip.name AS item_price,
                    ip.price_list,
                    ip.item_code,
                    i.item_name,
                    i.item_group,
                    ip.currency,
                    ip.uom AS price_uom,
                    ip.price_list_rate,
                    ucd.uom AS conv_uom,
                    ucd.conversion_factor,
                    ip.customer,
                    (1 / ucd.conversion_factor) * ip.price_list_rate as price_conv
                FROM
                    `tabItem Price` ip
                        JOIN
                    `tabItem` i ON i.item_code = ip.item_code
                        JOIN
                    `tabItem Group` ig_products ON ig_products.name = 'Products'
                        JOIN
                    `tabItem Group` ig_item ON ig_item.name = i.item_group
                        AND ig_item.lft BETWEEN ig_products.lft AND ig_products.rgt
                        LEFT JOIN
                    `tabUOM Conversion Detail` ucd ON ucd.parenttype = 'Item'
                        AND ucd.parent = i.name
                        AND ucd.uom = COALESCE(ip.uom, i.stock_uom)
                WHERE
                    ip.selling = 1 AND ip.docstatus < 2
                ORDER BY ip.item_code , CASE
                    WHEN COALESCE(ip.uom, i.stock_uom) = i.stock_uom THEN 0
                    ELSE 1
                END , CASE
                    WHEN ip.customer IS NULL OR ip.customer = '' THEN 0
                    ELSE 1
                END
                    """, as_dict=1)
            for d in data:
                if d.item_code not in price_map and d.price_conv:
                    price_map[d.item_code] = d.price_conv

        elif source == "Sales Invoice":
            data = frappe.db.sql("""
                SELECT
                    t.item_code,
                    t.item_name,
                    t.sales_invoice,
                    t.posting_date,
                    t.uom,
                    t.qty,
                    t.rate,
                    t.conversion_factor,
                    (t.rate / NULLIF(t.conversion_factor, 0)) AS price_conv
                FROM (
                    SELECT
                        sii.item_code,
                        sii.item_name,
                        sii.parent AS sales_invoice,
                        si.posting_date,
                        sii.uom,
                        sii.qty,
                        sii.rate,
                        sii.conversion_factor,
                        ROW_NUMBER() OVER (
                            PARTITION BY sii.item_code
                            ORDER BY si.posting_date DESC, si.posting_time DESC, si.creation DESC, sii.creation DESC
                        ) AS rn
                    FROM `tabSales Invoice Item` sii
                    JOIN `tabSales Invoice` si
                        ON si.name = sii.parent
                    JOIN `tabItem` i
                        ON i.item_code = sii.item_code
                    WHERE
                        si.docstatus = 1
                        AND IFNULL(si.is_return, 0) = 0
                        AND i.stock_uom = 'Kg'
                ) t
                WHERE t.rn = 1
                ORDER BY t.item_code;
                """, as_dict=1)
            
            for d in data:
                if d.item_code not in price_map and d.price_conv:
                    price_map[d.item_code] = d.price_conv
        else:
            # from Valuation rate
            data = frappe.db.sql("""
                SELECT
                    x.item_code,
                    x.item_name,
                    x.warehouse,
                    x.posting_date,
                    x.posting_time,
                    x.voucher_type,
                    x.voucher_no,
                    x.actual_qty,
                    x.incoming_rate as price_conv,
                    x.valuation_rate
                FROM (
                    SELECT
                        sle.item_code,
                        i.item_name,
                        sle.warehouse,
                        sle.posting_date,
                        sle.posting_time,
                        sle.voucher_type,
                        sle.voucher_no,
                        sle.actual_qty,
                        sle.incoming_rate,
                        sle.valuation_rate,
                        ROW_NUMBER() OVER (
                            PARTITION BY sle.item_code
                            ORDER BY
                                sle.posting_date DESC,
                                sle.posting_time DESC,
                                sle.creation DESC
                        ) AS rn
                    FROM
                        `tabStock Ledger Entry` sle
                    JOIN
                        `tabItem` i
                        ON i.item_code = sle.item_code
                    JOIN
                        `tabItem Group` ig_products
                        ON ig_products.name = 'Products'
                    JOIN
                        `tabItem Group` ig_item
                        ON ig_item.name = i.item_group
                        AND ig_item.lft BETWEEN ig_products.lft AND ig_products.rgt   -- include child groups
                    WHERE
                        sle.docstatus = 1
                        AND sle.is_cancelled = 0
                        AND sle.actual_qty > 0              -- incoming only
                        AND IFNULL(sle.incoming_rate, 0) != 0
                ) x
                WHERE
                    x.rn = 1
                ORDER BY
                    x.item_code
                """, as_dict=1)
            
            for d in data:
                if d.item_code not in price_map and d.price_conv:
                    price_map[d.item_code] = d.price_conv

        return price_map


    def get_data(self):
        wip_accounts = self.get_wip_accounts()
        if not wip_accounts:
            self.raw_data = []
            return

        # Kembangkan query_new milik Anda: GL-first, WIP akun dinamis, filter dinamis,
        # dan MAP Price dari Item Price('MAP') dengan fallback SLE valuation_rate.
        query_new = (
            """
            SELECT
                se.work_order AS work_order,
                wo.production_item AS produced_item,
                wo.qty,
                it.item_name AS product_name,
                gl.account AS account,
                SUM(gl.debit - gl.credit) AS amount
            FROM `tabGL Entry` gl
            JOIN `tabStock Entry` se
                ON gl.voucher_type = 'Stock Entry' AND gl.voucher_no = se.name
            JOIN `tabWork Order` wo
                ON wo.name = se.work_order
            LEFT JOIN `tabItem` it
                ON it.name = wo.production_item
            WHERE
                gl.is_cancelled = 0
                AND se.docstatus = 1
                AND se.company = %(company)s
                AND se.work_order IS NOT NULL
                AND gl.account IN %(accounts)s
                {cond}
            GROUP BY se.work_order, wo.production_item, it.item_name, gl.account
            HAVING ABS(SUM(gl.debit - gl.credit)) > 0.0001
            ORDER BY ABS(SUM(gl.debit - gl.credit)) DESC
            """
        ).format(cond=self.cond)

        rows = frappe.db.sql(
            query_new,
            {"company": self.company, "accounts": tuple(wip_accounts), **self.filters},
            as_dict=True,
        )

        if not rows:
            self.raw_data = []
            return

        # Normalize currency outputs
        je_data = self.get_journal_entry(wip_accounts)
        price_map = self.get_item_price_map(self.filters.price_source)
        data = []
        for r in rows:
            key = (r.account, r.work_order)
            if key in je_data:
                r.amount += je_data[key]
            
            if not r.amount:
                continue

            map_price = flt(price_map.get(r.produced_item))

            data.append(
                {
                    "work_order": r.work_order,
                    "produced_item": r.produced_item,
                    "product_name": r.product_name,
                    "account": r.account,
                    "amount": r.amount,
                    "qty": r.qty,
                    "currency": self.company_currency,
                    "map_price": map_price,
                    "map_currency": self.company_currency,
                }
            )

        self.raw_data = data

    def get_journal_entry(self, wip_accounts):
        wo_amount_map = {}
        for account in wip_accounts:
            data = frappe.db.sql("""
                SELECT 
                    jea.reference_name,
                    (IFNULL(jea.debit, 0) - IFNULL(jea.credit, 0)) AS amount
                FROM
                    `tabJournal Entry Account` jea
                WHERE
                    jea.docstatus = 1 and
                    jea.account = %s
                        AND jea.reference_type = 'Work Order'
                        AND IFNULL(jea.reference_name, '') != ''
                        AND (IFNULL(jea.debit, 0) != 0
                        OR IFNULL(jea.credit, 0) != 0)
                ORDER BY jea.reference_name;
            """, (account), as_dict=1)
            for d in data:
                key = (account, d.reference_name)
                wo_amount_map.setdefault(key, d.amount)
        return wo_amount_map

    def get_operation_account_map(self):
        rows = frappe.get_all(
            "Operation WIP Account",
            filters={
                "parent": self.company,
                "parenttype": "Company",
                "parentfield": "operation_wip_account",
            },
            fields=["operation", "wip_account"],
        )
        return {r.operation: r.wip_account for r in rows if r.wip_account}

    def process_data(self):
        # Group rows by account and order accounts: Seeding, Transplanting, Harvesting, then others
        rows = self.raw_data or []
        acc_map = self.get_operation_account_map()
        priority_accounts = []
        for op in ("Seeding", "Transplanting", "Harvesting"):
            acc = acc_map.get(op)
            if acc and acc not in priority_accounts:
                priority_accounts.append(acc)

        # Discover other accounts from data
        present_accounts = []
        for r in rows:
            acc = r.get("account")
            if acc and acc not in present_accounts:
                present_accounts.append(acc)

        other_accounts = [a for a in present_accounts if a not in priority_accounts]
        # Final account order
        account_order = priority_accounts + other_accounts

        # Build ordered list with group totals and a blank row between groups
        ordered = []
        for idx, acc in enumerate(account_order):
            group_rows = [d for d in rows if d.get("account") == acc]
            if not group_rows:
                continue

            ordered.extend(group_rows)

            total_amount = sum((r.get("amount") or 0) for r in group_rows)
            ordered.append({
                "work_order": "",
                "produced_item": "",
                "product_name": "Total",
                "account": acc,
                "amount": total_amount,
                "currency": self.company_currency,
                "map_currency": self.company_currency,
            })

            if idx < len(account_order) - 1:
                ordered.append({"currency": self.company_currency, "map_currency": self.company_currency})  # blank separator row

        # If no account ordering was matched, just pass through
        self.data = ordered if ordered else rows

    def execute(self):
        self.setup_condition()
        self.setup_column()
        self.get_data()
        self.process_data()

        return self.columns, self.data