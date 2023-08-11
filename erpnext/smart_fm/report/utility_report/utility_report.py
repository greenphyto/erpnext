import frappe
from frappe.utils import flt,cint,getdate

def execute(filters={}):
    return Report(filters).run()

class Report:
    def __init__(self, filters):
        self.filters = filters
        self.columns = []
        self.data = []
        self.chart = []

    def setup_conditions(self):
        self.conditions = ""
        if self.filters.get("type_of_meter"):
            self.conditions += " and u.type_of_meter = %(type_of_meter)s "
        elif self.filters.get("utility"):
            self.conditions += " and u.name = %(utility)s "

        self.filters.date_from = self.filters.get("date_from") or getdate("2000-01-01")
        self.filters.date_to = self.filters.get("date_to") or getdate("2099-01-01")

        if self.filters.get("date_from") and self.filters.get("date_to"):
            self.conditions += " and m.reading_date between %(date_from)s and %(date_to)s "


    def get_columns(self):
        self.columns = [
            { "fieldname": "meter_id" ,         "label": "Meter ID",        "fieldtype": "Link",    "width": 120, "options": "Utility"},
            { "fieldname": "current_reading" ,  "label": "Value",           "fieldtype": "Int",     "width": 120, "options": ""},
            { "fieldname": "reading_date" ,     "label": "Date",            "fieldtype": "Date",    "width": 120, "options": ""},
            { "fieldname": "type_of_meter" ,    "label": "Type of Meter",   "fieldtype": "Data",    "width": 150, "options": ""},
            { "fieldname": "meter_location" ,   "label": "Meter Location",  "fieldtype": "Data",    "width": 150, "options": ""}
        ]

    def get_data(self):
        self.raw_data = frappe.db.sql("""
            SELECT 
                *
            FROM
                (SELECT DISTINCT
                    m.meter_id,
                        m.current_reading,
                        m.reading_date,
                        m.reader_nameid,
                        u.type_of_meter,
                        u.meter_location
                FROM
                    `tabMeter Reading` m
                LEFT JOIN `tabUtility` u ON u.name = m.meter_id
                WHERE 
                    m.docstatus = 1
                    {}
                ORDER BY u.reading_date DESC
            ) AS m1
            GROUP BY m1.meter_id
        """.format(self.conditions), self.filters, as_dict=1)

    def process_data(self):
        self.data = self.raw_data

    def get_chart(self):
        pass

    def run(self):
        self.setup_conditions()
        self.get_columns()
        self.get_data()
        self.process_data()
        self.get_chart()

        return self.columns, self.data, None, self.chart