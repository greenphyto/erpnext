import os

import frappe
from openpyxl import Workbook

COMPANY = "Greenphyto Tech Sdn Bhd"
YEAR_START = "2026-01-01"
YEAR_END = "2026-12-31"

"""
Export candidates:
    bench --site erp-prod execute erpnext.patches.gp.export_cost_center_candidates_2026.execute

Apply (dry run, default):
    bench --site erp-prod execute erpnext.patches.gp.export_cost_center_candidates_2026.apply

Apply (real update):
    bench --site erp-prod execute erpnext.patches.gp.export_cost_center_candidates_2026.apply --kwargs "{'dry_run': False}"
"""


def get_mapping():
    settings = frappe.get_doc("Cost Center Settings", COMPANY)
    mapping = {}
    for row in settings.cost_center:
        if row.cost_center:
            mapping[row.account] = row.cost_center
    return mapping


def get_candidates(mapping):
    accounts = list(mapping.keys())
    if not accounts:
        return []

    gl = frappe.get_all(
        "GL Entry",
        filters={
            "company": COMPANY,
            "account": ["in", accounts],
            "posting_date": ["between", [YEAR_START, YEAR_END]],
            "is_cancelled": 0,
        },
        fields=[
            "name",
            "voucher_type",
            "voucher_no",
            "posting_date",
            "account",
            "debit",
            "credit",
            "cost_center",
        ],
        order_by="posting_date asc, voucher_no asc",
    )

    candidates = []
    for e in gl:
        expected = mapping.get(e.account)
        if expected and e.cost_center != expected:
            e.expected_cost_center = expected
            candidates.append(e)
    return candidates


def execute():
    mapping = get_mapping()
    if not mapping:
        print("No account->cost_center mapping found in Cost Center Settings for %s" % COMPANY)
        return

    candidates = get_candidates(mapping)

    wb = Workbook()
    ws = wb.active
    ws.title = "CC Candidates"
    ws.append(
        [
            "Voucher Type",
            "Voucher Name",
            "Date",
            "Account",
            "Debit",
            "Credit",
            "Current Cost Center",
            "Expected Cost Center",
        ]
    )
    for i, e in enumerate(candidates, start=1):
        print(
            "  [%d/%d] %s | %s | %s | %s | Dr %s Cr %s | %s -> %s"
            % (
                i,
                len(candidates),
                e.voucher_type,
                e.voucher_no,
                str(e.posting_date),
                e.account,
                e.debit,
                e.credit,
                e.cost_center,
                e.expected_cost_center,
            )
        )
        ws.append(
            [
                e.voucher_type,
                e.voucher_no,
                str(e.posting_date),
                e.account,
                e.debit,
                e.credit,
                e.cost_center,
                e.expected_cost_center,
            ]
        )

    out = os.path.expanduser("~/MY_CHANGE_CANDIDATE.xlsx")
    wb.save(out)
    print("Candidates (cost center mismatch): %d" % len(candidates))
    print("Saved to: %s" % out)


def apply(dry_run=True):
    mapping = get_mapping()
    if not mapping:
        print("No account->cost_center mapping found in Cost Center Settings for %s" % COMPANY)
        return

    candidates = get_candidates(mapping)
    print("Candidates to update: %d (dry_run=%s)" % (len(candidates), dry_run))

    updated = 0
    for i, e in enumerate(candidates, start=1):
        print(
            "  [%d/%d] %s | %s | %s | %s -> %s"
            % (
                i,
                len(candidates),
                e.voucher_type,
                e.voucher_no,
                e.account,
                e.cost_center,
                e.expected_cost_center,
            )
        )
        if not dry_run:
            frappe.db.set_value(
                "GL Entry",
                e.name,
                "cost_center",
                e.expected_cost_center,
                update_modified=False,
            )
            updated += 1

    if dry_run:
        print("Dry run only. No changes committed. Re-run with --kwargs \"{'dry_run': False}\" to apply.")
    else:
        frappe.db.commit()
        print("Updated %d GL Entry rows and committed." % updated)
