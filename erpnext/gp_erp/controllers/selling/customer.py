import frappe
from frappe import _
from frappe.model.naming import parse_naming_series
from frappe.utils import cint, cstr, flt
from frappe.contacts.doctype.address.address import get_address_templates

from erpnext.selling.doctype.customer.customer import Customer


class CustomerGP(Customer):
    def validate(self):
        super(CustomerGP, self).validate()
        self.set_code()
        self.set_default_customer_address()
        self.validate_sku()
        self.validate_customer_packaging()

    def set_code(self, force=False):
        comp_abbr = cstr(frappe.get_value("Company", self.company, "series_abbr"))
        series = comp_abbr + "C.#####"
        cash_sales = comp_abbr + "C00008"
        if self.is_cash_sales:
            self.customer_code = cash_sales

        if self.customer_code:
            if self.customer_code == cash_sales or force:
                return
            else:
                exist = frappe.get_value(
                    "Customer",
                    {"customer_code": self.customer_code, "name": ["!=", self.name]},
                )
                if exist:
                    frappe.throw(_(f"<b>{self.customer_code}</b> already use by {exist}"))

        if not self.customer_code:
            self.customer_code = parse_naming_series(series, doc=self)

    def validate_sku(self):
        self.total_item = 0
        done = []
        error_list = []
        done_sku = []
        dupp_list = []
        for d in self.get("customer_sku"):
            d.sku = cstr(d.sku).strip()
            if not d.sku_name:
                d.sku_name = d.origin_name

            self.total_item += 1
            if d.item_code not in done:
                done.append(d.item_code)
            else:
                error_list.append(f"<li>Row {d.idx}, Item {d.item_code}</li>")

            if d.sku not in done_sku:
                done_sku.append(d.sku)
            else:
                dupp_list.append(f"<li>Row {d.idx}, with SKU <b>{d.sku}</b></li>")

        if error_list:
            error = "".join(error_list)
            frappe.throw(_(f"<p>Found multiple item in SKU table:</p><ol>{error}</ol>"))

        if dupp_list:
            error = "".join(dupp_list)
            frappe.throw(
                _(f"<p>Found dupplciate SKU numbers:</p><ol>{error}</ol>")
            )

    def get_item_sku(self, item_code, field="sku"):
        for d in self.get("customer_sku"):
            if d.item_code == item_code:
                res = d.get(field)
                if field == "sku_name" and d.sku and not res:
                    res = d.get("origin_name")
                return res

    def set_default_customer_address(self):
        if self.customer_primary_address:
            return

        filters = [
            ["Dynamic Link", "link_doctype", "=", "Customer"],
            ["Dynamic Link", "link_name", "=", self.name],
        ]
        address = frappe.get_all("Address", filters=filters, fields=["*"]) or {}
        if address:
            address_as_dict = address[0]
            name, address_template = get_address_templates(address_as_dict)
            data = {
                "name": address_as_dict.get("name"),
                "address": frappe.render_template(address_template, address_as_dict),
            }
            self.customer_primary_address = data["name"]
            self.primary_address = data["address"]

    def validate_customer_packaging(self):
        seen = {}
        error_list = []

        for row in self.get("customer_packaging") or []:
            item_code = cstr(row.item_code).strip()
            package = cstr(row.package).strip()
            key = (item_code, package)

            if key not in seen:
                seen[key] = row.idx
                continue

            error_list.append(
                "<li>Row {0}, Item <b>{1}</b>, Package <b>{2}</b> (already used in Row {3})</li>".format(
                    row.idx,
                    frappe.bold(item_code or "-"),
                    frappe.bold(package or "-"),
                    seen[key],
                )
            )

        if error_list:
            error = "".join(error_list)
            frappe.throw(
                _(
                    "<p>Found duplicate item and package combinations in Customer Packaging:</p><ol>{0}</ol>"
                ).format(error)
            )

    def after_rename(self, olddn, newdn, merge=False):
        super(CustomerGP, self).after_rename(olddn, newdn, merge)
        if frappe.defaults.get_global_default("cust_master_name") == "Customer Name":
            self.db_set("customer_id", newdn)


def has_permission(doc, user):
    if user == "Administrator":
        return True
    if doc.is_internal_customer:
        return True


@frappe.whitelist()
def get_all_product(customer):
    rows = frappe.db.sql(
        """
        SELECT item.name AS item_code, item.item_name AS item_name,
               item.default_packaging AS package, pla.package_item AS packaging
        FROM `tabItem` item
        LEFT JOIN `tabPackaging List Available` pla
            ON pla.packaging = item.default_packaging AND pla.parent = item.name
        WHERE item.item_group = 'Products' AND item.disabled = 0
        ORDER BY item.name
    """,
        as_dict=True,
    )
    default_packaging = frappe.db.get_single_value(
        "Manufacturing Settings", "default_packaging"
    )
    for d in rows:
        if not d.packaging:
            d.packaging = default_packaging
    return rows
