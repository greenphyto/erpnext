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
        self.conditions = []


    def get_columns(self):
        self.columns = [
            { "fieldname": "" , "label": "", "fieldtype": "Data", "width": 100, "options": ""}
        ]

    def get_data(self):
        self.raw_data = frappe.db.sql("""
            select * from tabItem limit 10
        """)

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