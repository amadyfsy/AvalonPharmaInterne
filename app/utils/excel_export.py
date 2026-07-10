from openpyxl import Workbook
import os
import uuid

def export_to_excel(headers, data, sheet_title="Export", output_filename=None):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title
    
    ws.append(headers)
    for row in data:
        ws.append(row)
        
    if not output_filename:
        output_filename = f"{uuid.uuid4().hex}.xlsx"
        
    excel_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'uploads', 'exports')
    if not os.path.exists(excel_dir):
        os.makedirs(excel_dir)
        
    filepath = os.path.join(excel_dir, output_filename)
    wb.save(filepath)
    return filepath
