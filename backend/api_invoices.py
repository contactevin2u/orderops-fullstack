"""FastAPI endpoints for invoice PDFs."""
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

from .pdf_invoice import build_invoice_pdf

app = FastAPI()


def _mock_invoice(inv_id: int) -> dict:
    """Return a mock invoice structure for demonstration."""
    return {
        "number": f"INV-{inv_id:04d}",
        "date": "2024-06-01",
        "delivery_date": "2024-06-05",
        "due_date": "2024-06-15",
        "bill_to": {
            "name": "John Doe",
            "address": ["123 Main St", "Springfield", "USA"],
            "phone": "+123456789",
            "email": "john@example.com",
        },
        "ship_to": {
            "name": "John Doe",
            "address": ["123 Main St", "Springfield", "USA"],
        },
        "items": [
            {"description": "Widget A", "sku": "WID-A", "qty": 2, "unit_price": 50},
            {"description": "Widget B", "sku": "WID-B", "qty": 1, "unit_price": 100},
        ],
        "discount": 0,
        "tax_rate": 0.06,
        "delivery_fee": 10,
        "amount_paid": 0,
        "notes": "Thank you for your business.",
        "terms": ["Payment due within 30 days", "Goods sold are not refundable"],
    }


async def get_invoice_from_db(inv_id: int) -> dict | None:
    """Stub function to fetch invoice data.

    Replace with real database access in production.
    """
    # Here we simply return mock data. In real usage, return None if not found.
    return _mock_invoice(inv_id)


@app.get("/api/invoices/{inv_id}/pdf")
async def invoice_pdf(inv_id: int) -> Response:
    """Return the invoice PDF for the given invoice id."""
    invoice = await get_invoice_from_db(inv_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    pdf_bytes = await build_invoice_pdf(invoice)
    headers = {
        "Content-Disposition": f'inline; filename="{invoice["number"]}.pdf"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
