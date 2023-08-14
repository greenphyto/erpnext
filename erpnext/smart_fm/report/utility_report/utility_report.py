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
        pass


    def get_columns(self):
        self.columns = [
            { "fieldname": "meter_id" ,         "label": "Meter ID",        "fieldtype": "Link",    "width": 120, "options": "Utility"},
            { "fieldname": "current_reading" ,  "label": "Value",           "fieldtype": "Int",     "width": 120, "options": ""},
            { "fieldname": "reading_date" ,     "label": "Date",            "fieldtype": "Date",    "width": 120, "options": ""},
            { "fieldname": "type_of_meter" ,    "label": "Type of Meter",   "fieldtype": "Data",    "width": 150, "options": ""},
            { "fieldname": "meter_location" ,   "label": "Meter Location",  "fieldtype": "Data",    "width": 150, "options": ""}
        ]

    def get_data(self):
        self.raw_data = get_last_meter_data(self.filters);

    def process_data(self):
        self.data = self.raw_data

    def get_chart(self):
        self.chart = []
        if not self.filters.get("type_of_meter"):
            return
        
        labels = []
        datasets = []
        values = []

        for d in self.data:
            if not d.meter_id in labels:
                labels.append(d.meter_id)
            
            values.append(d.current_reading)

        datasets.append({
            "name": d.meter_id,
            "values": values
        })

        
        self.chart = {
            "data": {
                "labels": labels, 
                "datasets": datasets
            }, 
            "colors": ['yellow', 'orange', 'green'],
            "type": "bar"
        }


    def run(self):
        self.setup_conditions()
        self.get_columns()
        self.get_data()
        self.process_data()
        self.get_chart()

        return self.columns, self.data, None, self.chart

def get_last_meter_data(filters):
    conditions = ""
    if filters.get("type_of_meter"):
        conditions += " and u.type_of_meter = %(type_of_meter)s "
    elif filters.get("utility"):
        conditions += " and u.name = %(utility)s "
    if filters.get("reading_date"):
        conditions += " and m.reading_date <= %(reading_date)s "

    data = frappe.db.sql("""
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
                         
        """.format(conditions), filters, as_dict=1)

    return data