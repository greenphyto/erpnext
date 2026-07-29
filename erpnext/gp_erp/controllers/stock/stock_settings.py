import frappe
from frappe import _

from erpnext.stock.doctype.stock_settings.stock_settings import StockSettings


class StockSettingsGP(StockSettings):
    def get_missing_item_price(self):
        return frappe.db.sql("""
            SELECT
                i.item_code,
                i.item_name,
                i.item_group,
                ucd.uom,
                ucd.conversion_factor,
                ip.price_list_rate AS rate
            FROM `tabItem` i
            LEFT JOIN `tabUOM Conversion Detail` ucd
                ON ucd.parent = i.item_code
            LEFT JOIN `tabItem Price` ip
                ON ip.item_code = i.item_code
                AND ip.selling = 1
                AND (ip.customer IS NULL OR ip.customer = '')
                AND ip.uom = ucd.uom
            WHERE i.item_group = 'Products'
                AND i.disabled = 0
                AND (
                    ip.name IS NULL
                    OR ip.uom != ucd.uom
                )
            ORDER BY i.item_code, ucd.uom
        """, as_dict=True)
