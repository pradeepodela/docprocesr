import json
import re
from typing import Any, Dict, List
from mistralai import Mistral, TextChunk, ImageURLChunk
from openai import OpenAI
from config import Config
from models import InvoiceData

# Initialize clients
mistral_client = Mistral(api_key=Config.MISTRAL_API_KEY) if Config.MISTRAL_API_KEY else None
openrouter_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=Config.OPENROUTER_API_KEY) if Config.OPENROUTER_API_KEY else None

def _create_invoice_extraction_prompt(ocr_text: str) -> str:
    """Create the prompt for invoice data extraction"""
    return f"""
You are an expert invoice data extraction specialist. Extract ALL information from the invoice OCR text below and convert it into structured JSON format.
**CRITICAL INSTRUCTIONS:**
1. **Extract ALL line items** - Don't miss any products/services listed
2. **Be precise with numbers** - Extract exact quantities, prices, and totals as numbers (not strings)
3. **Date format** - Use YYYY-MM-DD format for all dates
4. **Currency** - Remove currency symbols, keep only numeric values
5. **Line item details** - For each item, extract description, quantity, unit price, and total
6. **Vendor/Customer info** - Extract all available contact information
7. **Calculations** - Ensure subtotal, tax, and total amounts are correctly captured
8. **Handle missing data** - Use empty strings for missing text fields, 0.0 for missing numbers, empty arrays for missing lists
**JSON STRUCTURE REQUIRED:**
{{
    "invoice_number": "string",
    "invoice_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD or null",
    "vendor_name": "string",
    "vendor_address": "string or null",
    "vendor_phone": "string or null",
    "vendor_email": "string or null",
    "vendor_tax_id": "string or null",
    "customer_name": "string or null",
    "customer_address": "string or null",
    "customer_phone": "string or null",
    "customer_email": "string or null",
    "gst_number": "string or null",
    "line_items": [
        {{
            "description": "string",
            "quantity": number,
            "unit_price": number,
            "total_price": number,
            "unit": "string or null",
            "sku": "string or null",
            "tax_rate": number or null
        }}
    ],
    "subtotal": number,
    "tax_amount": number or null,
    "discount_amount": number,
    "total_amount": number,
    "currency": "string",
    "payment_terms": "string or null",
    "notes": "string or null"
}}
**IMPORTANT:** 
- If a field is not present in the invoice, use appropriate defaults (empty string for text, 0.0 for numbers, null for optional fields)
- For required fields, make reasonable inferences from context
- Pay special attention to line items - extract every single item listed
- Ensure all monetary amounts are numeric (no currency symbols)
- Use 0.0 for missing numeric values, not null
**OCR TEXT:**
{ocr_text}
**RESPONSE FORMAT:**
Return ONLY valid JSON that matches the structure above. Include all line items found in the invoice.
"""

def _mistral_parse(chunks) -> Dict[str, Any]:
    """Parse invoice data using Mistral"""
    if not mistral_client:
        raise RuntimeError("Mistral API key not configured")
    
    try:
        chat = mistral_client.chat.parse(
            model=Config.DEFAULT_MODEL,
            messages=[{"role": "user", "content": chunks}],
            response_format=InvoiceData,
            temperature=0,
        )
        return json.loads(chat.choices[0].message.parsed.model_dump_json())
    except Exception as e:
        # If structured parsing fails, try regular chat completion
        print(f"Structured parsing failed, trying regular completion: {str(e)}")
        chat = mistral_client.chat.complete(
            model=Config.DEFAULT_MODEL,
            messages=[{"role": "user", "content": chunks}],
            temperature=0,
        )
        raw_response = chat.choices[0].message.content
        return _extract_json(raw_response)

def _extract_json(text: str) -> dict:
    """Extract the first JSON block from text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        raise ValueError("Failed to extract valid JSON from OpenRouter response.")

def _openrouter_parse(prompt_text, img_url) -> Dict[str, Any]:
    """Parse invoice data using OpenRouter"""
    if not openrouter_client:
        raise RuntimeError("OpenRouter API key not configured")
    
    content = []
    if img_url:
        content.append({"type": "image_url", "image_url": {"url": img_url}})
    content.append({"type": "text", "text": prompt_text})
    
    completion = openrouter_client.chat.completions.create(
        model=Config.OPENROUTER_MODEL,
        messages=[{"role": "user", "content": content}],
        temperature=0,
        extra_headers={
            "X-Title": "BulkInvoiceCSV",
            "HTTP-Referer": "https://localhost"
        },
    )
    raw = completion.choices[0].message.content.strip()
    return _extract_json(raw)