import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, add_days

from erpnext.stock.doctype.batch.batch import Batch, get_batch_qty, get_batches


class BatchGP(Batch):
    def autoname(self):
        super(BatchGP, self).autoname()
        if self.flags.add_last_symbol:
            self.batch_id += "-" + str(self.flags.add_last_symbol)
        self.name = self.batch_id

    def validate(self):
        self.item_has_batch_enabled()
        self.set_batchwise_valuation()
        self.set_status()

    def set_status(self):
        self.status = _get_batch_status(self.batch_qty, self.expiry_date)

    def before_save(self):
        has_expiry_date, shelf_life_in_days = _get_item_shelf_life_in_days(
            self.item, self.get("reference_doctype"), self.get("reference_name")
        )
        if not self.expiry_date and has_expiry_date and shelf_life_in_days:
            self.expiry_date = add_days(self.manufacturing_date, shelf_life_in_days)
        if has_expiry_date and not self.expiry_date:
            frappe.throw(
                msg=_("Please set {0} for Batched Item {1}, which is used to set {2} on Submit.").format(
                    frappe.bold("Expiry Date"),
                    frappe.bold(self.item),
                    frappe.bold("Manufacturing Date"),
                )
            )


def _get_batch_status(batch_qty, expiry_date):
    if flt(batch_qty) <= 0:
        return "Empty"
    if expiry_date and getdate(expiry_date) < getdate():
        return "Expired"
    return "Active"


def _get_item_shelf_life_in_days(item_code, reference_doctype=None, reference_name=None):
    has_expiry_date, shelf_life_in_days = frappe.db.get_value(
        "Item", item_code, ["has_expiry_date", "shelf_life_in_days"]
    ) or (0, None)
    if not (reference_doctype and reference_name):
        return has_expiry_date, shelf_life_in_days
    if not frappe.db.exists("DocType", reference_doctype):
        return has_expiry_date, shelf_life_in_days
    meta = frappe.get_meta(reference_doctype)
    if not meta.has_field("company"):
        return has_expiry_date, shelf_life_in_days
    reference_company = frappe.db.get_value(reference_doctype, reference_name, "company")
    if not reference_company:
        return has_expiry_date, shelf_life_in_days
    mapped_shelf_life = frappe.db.get_value(
        "Shell Life Companies",
        {"parent": item_code, "parenttype": "Item", "company": reference_company},
        "shelf_life_in_days",
    )
    if mapped_shelf_life is not None:
        shelf_life_in_days = mapped_shelf_life
    return has_expiry_date, shelf_life_in_days


def get_available_batch(item_code, qty, skip_wip_warehouse=False, company="", date=""):
    import erpnext
    from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import (
        get_item_warehouse_batch_map,
    )

    if not skip_wip_warehouse:
        wip_warehouse = get_wip_warehouse()
    else:
        wip_warehouse = []
    start_date = getdate("2000-01-01")
    end_date = getdate(date)
    company = company or erpnext.get_default_company()
    filters = frappe._dict(
        {"company": company, "from_date": start_date, "to_date": end_date, "item_code": item_code}
    )
    iwb_map = get_item_warehouse_batch_map(filters, float_precision=4)
    result = []
    for item, val in iwb_map.items():
        for wh in sorted(val):
            for batch in sorted(val[wh]):
                qty_dict = val[wh][batch]
                if qty_dict.bal_qty > qty and wh not in wip_warehouse:
                    result.append(
                        frappe._dict({"batch_id": batch, "qty": qty_dict.bal_qty, "warehouse": wh})
                    )

    return result


def get_available_batch_portion(item_code, qty, skip_wip_warehouse=False, company="", date="", strategy="FIFO"):
    from frappe.utils import nowdate

    import erpnext
    from erpnext.stock.report.batch_wise_balance_history.batch_wise_balance_history import (
        get_item_warehouse_batch_map,
    )

    if not skip_wip_warehouse:
        wip_warehouse = get_wip_warehouse()
    else:
        wip_warehouse = []

    start_date = getdate("2000-01-01")
    end_date = getdate(date or nowdate())
    today = getdate(nowdate())
    company = company or erpnext.get_default_company()

    filters = frappe._dict(
        {"company": company, "from_date": start_date, "to_date": end_date, "item_code": item_code}
    )

    iwb_map = get_item_warehouse_batch_map(filters, float_precision=4)
    batch_list = []

    for item, val in iwb_map.items():
        for wh in val:
            if wh in wip_warehouse:
                continue
            for batch_id in val[wh]:
                qty_dict = val[wh][batch_id]
                if qty_dict.bal_qty <= 0:
                    continue

                batch_doc = frappe.get_doc("Batch", batch_id)
                expiry = batch_doc.expiry_date or getdate("2099-12-31")
                if expiry < today:
                    continue

                batch_list.append(
                    frappe._dict(
                        {
                            "batch_id": batch_id,
                            "qty": qty_dict.bal_qty,
                            "warehouse": wh,
                            "expiry_date": expiry,
                            "creation": batch_doc.creation,
                        }
                    )
                )

    if strategy == "Expired First":
        batch_list.sort(key=lambda b: (b.expiry_date, b.batch_id))
    elif strategy == "Small First":
        batch_list.sort(key=lambda b: (b.qty, b.batch_id))
    else:
        batch_list.sort(key=lambda b: (b.creation, b.batch_id))

    result = []
    remaining = qty
    for b in batch_list:
        if remaining <= 0:
            break
        used = min(b.qty, remaining)
        result.append(frappe._dict({"batch_id": b.batch_id, "qty": used, "warehouse": b.warehouse}))
        remaining -= used
    return result if result else []


def get_wip_warehouse():
    data = [d.name for d in frappe.get_list("Warehouse", {"is_wip_warehouse": 1})]
    wip_settings = frappe.get_value(
        "Manufacturing Settings", "Manufacturing Settings", "default_wip_warehouse"
    )
    if wip_settings:
        data.append(wip_settings)

    return data


def set_batch_nos(doc, warehouse_field, throw=False, child_table="items"):
    """Automatically select `batch_no` for outgoing items in item table"""
    for d in doc.get(child_table):
        qty = d.get("stock_qty") or d.get("transfer_qty") or d.get("qty") or 0
        warehouse = d.get(warehouse_field, None)
        if warehouse and qty > 0 and frappe.db.get_value("Item", d.item_code, "has_batch_no"):
            if not d.batch_no:
                batch = get_batch_qty(item_code=d.item_code, warehouse=warehouse)
                if batch:
                    d.batch_no = batch[0].batch_no
                elif throw:
                    frappe.throw(
                        _("Row {0}: Batch No must be set for Item {1}").format(d.idx, d.item_code)
                    )
            else:
                batch_qty = get_batch_qty(batch_no=d.batch_no, warehouse=warehouse)
                if isinstance(batch_qty, list):
                    batch_qty = batch_qty[0].qty if batch_qty else 0
                if doc.docstatus == 1:
                    if flt(batch_qty, d.precision("qty")) < flt(qty, d.precision("qty")):
                        frappe.throw(
                            _(
                                "Row #{0}: The batch {1} has only {2} qty. Please select another batch which has {3} qty available."
                            ).format(d.idx, d.batch_no, batch_qty, qty)
                        )


def get_item_shelf_life_in_days(item_code, reference_doctype=None, reference_name=None):
    return _get_item_shelf_life_in_days(item_code, reference_doctype, reference_name)


def pick_batches(item_code, warehouse, qty, strategy="FIFO"):
    batches = get_batches(item_code, warehouse, qty)
    if not batches:
        return []
    result = []
    remaining = flt(qty)
    for batch in batches:
        if remaining <= 0:
            break
        pick_qty = min(flt(batch.qty), remaining)
        if pick_qty > 0:
            result.append(frappe._dict({"batch_no": batch.batch_no, "qty": pick_qty}))
            remaining -= pick_qty
    return result
