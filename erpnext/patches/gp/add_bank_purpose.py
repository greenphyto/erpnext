import frappe

def insert_default_bank_purposes():
    print("Inserting new Bank Purpose..")
    bank_purposes = [
        {"code": "BEXP", "purpose": "Business Expenses"},
        {"code": "BONU", "purpose": "Bonus Payment"},
        {"code": "CBTV", "purpose": "Cable TV Bill"},
        {"code": "CCRD", "purpose": "Credit Card Payment"},
        {"code": "CHAR", "purpose": "Charity Payment"},
        {"code": "COLL", "purpose": "Collection Payment"},
        {"code": "COMM", "purpose": "Commission"},
        {"code": "CPKC", "purpose": "Carpark Charges"},
        {"code": "CSDB", "purpose": "Cash Disbursement"},
        {"code": "DCRD", "purpose": "Debit Card Payment"},
        {"code": "DIVD", "purpose": "Dividend"},
        {"code": "DNTS", "purpose": "Dental Services"},
        {"code": "EDUC", "purpose": "Education"},
        {"code": "FCPM", "purpose": "Payment of Fees and Charges"},
        {"code": "FWLV", "purpose": "Foreign Worker Levy"},
        {"code": "GDDS", "purpose": "Purchase Sale Of Goods"},
        {"code": "GOVI", "purpose": "Government Insurance"},
        {"code": "GSTX", "purpose": "Goods & Services Tax"},
        {"code": "HSPC", "purpose": "Hospital Care"},
        {"code": "IHRP", "purpose": "Instalment Hire Purchase Agreement"},
        {"code": "INSU", "purpose": "Insurance Premium"},
        {"code": "INTC", "purpose": "Intra Company Payment"},
        {"code": "INTE", "purpose": "Interest"},
        {"code": "INVS", "purpose": "Investment & Securities"},
        {"code": "IVPT", "purpose": "Invoice Payment"},
        {"code": "LOAN", "purpose": "Loan"},
        {"code": "MDCS", "purpose": "Medical Services"},
        {"code": "NITX", "purpose": "Net Income Tax"},
        {"code": "OTHR", "purpose": "Other"},
        {"code": "PHON", "purpose": "Telephone Bill"},
        {"code": "PTXP", "purpose": "Property Tax"},
        {"code": "RDTX", "purpose": "Road Tax"},
        {"code": "REBT", "purpose": "Rebate"},
        {"code": "REFU", "purpose": "Refund"},
        {"code": "RENT", "purpose": "Rent"},
        {"code": "SALA", "purpose": "Salary Payment"},
        {"code": "STDY", "purpose": "Study"},
        {"code": "SUPP", "purpose": "Supplier Payment"},
        {"code": "TAXS", "purpose": "Tax Payment"},
        {"code": "TBIL", "purpose": "Telco Bill"},
        {"code": "TCSC", "purpose": "Town Council Service Charges"},
        {"code": "TRAD", "purpose": "Trade Services"},
        {"code": "TREA", "purpose": "Treasury Payment"},
        {"code": "TRPT", "purpose": "Transport"},
        {"code": "UBIL", "purpose": "Utilities"},
        {"code": "WHLD", "purpose": "With Holding"}
    ]

    for item in bank_purposes:
        if not frappe.db.exists("Bank Purpose", {"code": item["code"]}):
            doc = frappe.get_doc({
                "doctype": "Bank Purpose",
                "code": item["code"],
                "purpose": item["purpose"]
            })
            doc.insert(ignore_permissions=True)
