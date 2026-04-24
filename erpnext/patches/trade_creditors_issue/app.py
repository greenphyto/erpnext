import frappe
import pandas as pd
import os
from datetime import datetime

def inspect_excel():
    """Inspect the Excel file structure"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    excel_file = os.path.join(current_dir, 'Trade_Creditors_260424152311.xlsx')
    
    # Read first few rows without header
    df = pd.read_excel(excel_file, header=None, nrows=10)
    print("First 10 rows of the Excel file:")
    print(df.to_string())
    print("\n" + "="*80 + "\n")
    
    # Try reading with different header rows
    for header_row in [0, 1, 2, 3, 4]:
        try:
            df_test = pd.read_excel(excel_file, header=header_row)
            print(f"Columns when header is row {header_row}:")
            print(df_test.columns.tolist())
            print(f"First 3 data rows:")
            print(df_test.head(3).to_string())
            print("\n" + "="*80 + "\n")
        except:
            pass

def export_invoice_noumber():
    """
    - read Trade_Creditors_260424152311.xlsx and export to new csv
    - same folder
    - format: invoice_number, supplier, posting_date, due_date, total_oustanding_amount, paid_amount, unpaid_amount
    """
    # Get the directory path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    excel_file = os.path.join(current_dir, 'Trade_Creditors_260424152311.xlsx')
    csv_file = os.path.join(current_dir, 'Trade_Creditors_export.csv')
    
    # Read the Excel file with header at row 3
    df = pd.read_excel(excel_file, header=3)
    
    # Remove rows that are completely empty or summary rows (where Supplier or Voucher No is NaN)
    df = df.dropna(subset=['Supplier', 'Voucher No'])
    
    # Map Excel columns to desired output columns
    column_mapping = {
        'Voucher No': 'invoice_number',
        'Supplier': 'supplier',
        'Posting Date': 'posting_date',
        'Due Date': 'due_date',
        'Outstanding Amount': 'total_outstanding_amount',
        'Paid Amount': 'paid_amount',
    }
    
    # Select and rename columns
    df_export = df[list(column_mapping.keys())].copy()
    df_export.rename(columns=column_mapping, inplace=True)
    
    # Add status column based on due_date and outstanding_amount
    def determine_status(row):
        outstanding = row['total_outstanding_amount']
        due_date = row['due_date']
        
        # If outstanding is 0 or negative and paid amount exists
        if outstanding <= 0:
            return 'Paid'
        
        # If due_date is NaT (not a time), check outstanding
        if pd.isna(due_date):
            if outstanding > 0:
                return 'Unpaid'
            else:
                return 'Paid'
        
        # Convert due_date to datetime if it's not already
        if not isinstance(due_date, pd.Timestamp):
            due_date = pd.to_datetime(due_date)
        
        # Get current date
        today = pd.Timestamp(datetime.now().date())
        
        # Determine status based on due date and outstanding amount
        if outstanding > 0:
            if due_date < today:
                return 'Overdue'
            else:
                return 'Unpaid'
        else:
            return 'Paid'
    
    df_export['status'] = df_export.apply(determine_status, axis=1)
    
    # Add unpaid_amount (same as outstanding amount)
    df_export['unpaid_amount'] = df_export['total_outstanding_amount']
    
    # Check if invoice exists in GL Entry
    def check_gl_exists(invoice_number):
        if pd.isna(invoice_number):
            return 'NO'
        try:
            # Check if frappe is connected
            if not hasattr(frappe, 'db') or not frappe.db:
                return 'N/A'
            
            # Check if the voucher_no exists in GL Entry
            exists = frappe.db.exists('GL Entry', {'voucher_no': invoice_number})
            return 'YES' if exists else 'NO'
        except Exception as e:
            print(f"Error checking GL Entry for {invoice_number}: {str(e)}")
            return 'ERROR'
    
    print("Checking GL Entry for each invoice...")
    df_export['gl_exists'] = df_export['invoice_number'].apply(check_gl_exists)
    
    # Reorder columns to put status after due_date and gl_exists after status
    columns_order = [
        'invoice_number',
        'supplier', 
        'posting_date',
        'due_date',
        'status',
        'gl_exists',
        'total_outstanding_amount',
        'paid_amount',
        'unpaid_amount'
    ]
    df_export = df_export[columns_order]
    
    # Export to CSV
    df_export.to_csv(csv_file, index=False)
    
    print(f"Data exported successfully to: {csv_file}")
    print(f"Total rows exported: {len(df_export)}")
    print(f"\nFirst 5 rows:")
    print(df_export.head().to_string())
    
    return csv_file

if __name__ == "__main__":
    # Try to initialize frappe (optional, for GL Entry check)
    try:
        import sys
        sys.path.insert(0, '/workspace/development/gp-frappe-bench/sites')
        frappe.init(site='test5')
        frappe.connect()
        print("Frappe initialized successfully - GL Entry check enabled\n")
    except Exception as e:
        print(f"Warning: Could not initialize Frappe: {str(e)}")
        print("GL Entry check will be skipped (gl_exists will show 'N/A')")
        print("\nTo run with GL Entry check, use:")
        print("bench --site test5 execute erpnext.patches.trade_creditors_issue.run_export.run_export\n")
    
    # inspect_excel()  # Uncomment to inspect file structure
    export_invoice_noumber()