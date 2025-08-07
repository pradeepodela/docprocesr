from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class LineItem(BaseModel):
    description: str = Field(default="", description="Product/service description")
    quantity: float = Field(default=0.0, description="Quantity ordered")
    unit_price: float = Field(default=0.0, description="Price per unit")
    total_price: float = Field(default=0.0, description="Total price for this line item")
    unit: Optional[str] = Field(default=None, description="Unit of measurement (e.g., 'each', 'kg', 'hours')")
    sku: Optional[str] = Field(default=None, description="Product SKU or code")
    tax_rate: Optional[float] = Field(default=None, description="Tax rate for this item")

class InvoiceData(BaseModel):
    # Invoice Header
    invoice_number: str = Field(default="", description="Invoice number")
    invoice_date: str = Field(default="", description="Invoice date in YYYY-MM-DD format")
    due_date: Optional[str] = Field(default=None, description="Due date in YYYY-MM-DD format")
    gst_number: Optional[str] = Field(default=None, description="GST number for the invoice")
    
    # Vendor Information
    vendor_name: str = Field(default="", description="Vendor/supplier name")
    vendor_address: Optional[str] = Field(default=None, description="Vendor address")
    vendor_phone: Optional[str] = Field(default=None, description="Vendor phone number")
    vendor_email: Optional[str] = Field(default=None, description="Vendor email")
    vendor_tax_id: Optional[str] = Field(default=None, description="Vendor tax ID")
    
    # Customer Information
    customer_name: Optional[str] = Field(default=None, description="Customer name")
    customer_address: Optional[str] = Field(default=None, description="Customer address")
    customer_phone: Optional[str] = Field(default=None, description="Customer phone")
    customer_email: Optional[str] = Field(default=None, description="Customer email")
    
    # Line Items
    line_items: List[LineItem] = Field(default_factory=list, description="List of invoice line items")
    
    # Totals
    subtotal: float = Field(default=0.0, description="Subtotal amount")
    tax_amount: Optional[float] = Field(default=None, description="Total tax amount")
    discount_amount: Optional[float] = Field(default=0.0, description="Discount amount")
    total_amount: float = Field(default=0.0, description="Total invoice amount")
    
    # Additional fields
    currency: Optional[str] = Field(default="USD", description="Currency code")
    payment_terms: Optional[str] = Field(default=None, description="Payment terms")
    notes: Optional[str] = Field(default=None, description="Additional notes")