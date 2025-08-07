import pandas as pd
from typing import Any, Dict, List

def convert_invoices_to_csv(invoices: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert multiple invoices to a single CSV with line-item level detail"""
    rows = []
    
    for invoice_idx, invoice in enumerate(invoices, 1):
        # Extract invoice header data
        header_data = {
            'file_number': invoice_idx,
            'invoice_number': invoice.get('invoice_number', ''),
            'invoice_date': invoice.get('invoice_date', ''),
            'due_date': invoice.get('due_date', ''),
            'vendor_name': invoice.get('vendor_name', ''),
            'vendor_address': invoice.get('vendor_address', ''),
            'vendor_phone': invoice.get('vendor_phone', ''),
            'vendor_email': invoice.get('vendor_email', ''),
            'vendor_tax_id': invoice.get('vendor_tax_id', ''),
            'customer_name': invoice.get('customer_name', ''),
            'customer_address': invoice.get('customer_address', ''),
            'customer_phone': invoice.get('customer_phone', ''),
            'customer_email': invoice.get('customer_email', ''),
            'subtotal': invoice.get('subtotal', 0),
            'tax_amount': invoice.get('tax_amount', 0),
            'discount_amount': invoice.get('discount_amount', 0),
            'total_amount': invoice.get('total_amount', 0),
            'currency': invoice.get('currency', 'USD'),
            'payment_terms': invoice.get('payment_terms', ''),
            'notes': invoice.get('notes', ''),
            'gst_number': invoice.get('gst_number', ''),
        }
        
        # Process line items
        line_items = invoice.get('line_items', [])
        if not line_items:
            # If no line items, create one row with header data
            row = header_data.copy()
            row.update({
                'line_item_number': 1,
                'item_description': '',
                'quantity': 0,
                'unit_price': 0,
                'line_total': 0,
                'unit': '',
                'sku': '',
                'tax_rate': 0,
            })
            rows.append(row)
        else:
            # Create one row per line item
            for item_idx, item in enumerate(line_items, 1):
                row = header_data.copy()
                row.update({
                    'line_item_number': item_idx,
                    'item_description': item.get('description', ''),
                    'quantity': item.get('quantity', 0),
                    'unit_price': item.get('unit_price', 0),
                    'line_total': item.get('total_price', 0),
                    'unit': item.get('unit', ''),
                    'sku': item.get('sku', ''),
                    'tax_rate': item.get('tax_rate', 0),
                })
                rows.append(row)
    
    return pd.DataFrame(rows)

def create_summary_csv(invoices: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create a summary CSV with one row per invoice"""
    summary_rows = []
    
    for invoice_idx, invoice in enumerate(invoices, 1):
        line_items = invoice.get('line_items', [])
        summary_row = {
            'file_number': invoice_idx,
            'invoice_number': invoice.get('invoice_number', ''),
            'invoice_date': invoice.get('invoice_date', ''),
            'due_date': invoice.get('due_date', ''),
            'vendor_name': invoice.get('vendor_name', ''),
            'customer_name': invoice.get('customer_name', ''),
            'line_items_count': len(line_items),
            'subtotal': invoice.get('subtotal', 0),
            'tax_amount': invoice.get('tax_amount', 0),
            'discount_amount': invoice.get('discount_amount', 0),
            'total_amount': invoice.get('total_amount', 0),
            'currency': invoice.get('currency', 'USD'),
            'gst_number': invoice.get('gst_number', ''),
        }
        summary_rows.append(summary_row)
    
    return pd.DataFrame(summary_rows)