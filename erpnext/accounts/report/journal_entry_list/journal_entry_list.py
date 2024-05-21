import frappe, json
from frappe import _

def execute(filters=None):
    # set filters
    order = ""
    cond = ""
    if filters.get("order_by") == "Date":
        order = "a.posting_date DESC"
    else:
        order = "a.name DESC"

    if filters.get("name"):
        cond += " and a.name like '%"+filters.get("name")+"%' "


    # get column
    column = [
        {"label": _("Name"),            "fieldtype":"Data",    "fieldname": "name",             "width": 180},
		{"label": _("Date"),            "fieldtype":"Date",    "fieldname": "posting_date",     "width": 100},
        {"label": _("Status"),          "fieldtype":"Data",    "fieldname": "docstatus",        "width": 100},
        {"label": _("Entry Type"),      "fieldtype":"Data",    "fieldname": "voucher_type",     "width": 110},
        {"label": _("Company"),         "fieldtype":"Data",    "fieldname": "company",          "width": 150},
        {"label": _("Reference Number"),"fieldtype":"Data",    "fieldname": "cheque_no",      "width": 150},
        {"label": _("Total Debit"),     "fieldtype":"Currency",    "fieldname": "total_debit",      "width": 120},
        {"label": _("Remark"),     "fieldtype":"Data",    "fieldname": "remark",     "width": 200}
    ]

    # get data
    data = frappe.db.sql("""
        SELECT 
            a.*
        FROM
            (SELECT 
                j.name,
                    j.posting_date,
                    IF(j.docstatus = 0, 'Draft', IF(j.docstatus = 1, 'Submitted', 'Cancelled')) as docstatus,
                    "{{}}" as data,
                    j.voucher_type,
                    j.company,
                    j.cheque_no,
                    j.total_debit,
                    j.remark         
            FROM
                `tabJournal Entry` j UNION ALL SELECT 
                    d.deleted_name,
                    d.document_date,
                    'Deleted' AS docstatus,
                    d.data, d.name, d.name,d.name,d.name,d.name
            FROM
                `tabDeleted Document` d
            WHERE
                d.deleted_doctype = 'Journal Entry') a
        where a.name is not null {} 
                         ORDER BY {}
    """.format(cond, order), as_dict=1)

    # process
    final_data = []
    for d in data:
        if d.docstatus == "Deleted":
            dt = json.loads(d.data)
            dt["docstatus"] = "Deleted"
            final_data.append(dt)
        else:
            final_data.append(d)
    return column, final_data