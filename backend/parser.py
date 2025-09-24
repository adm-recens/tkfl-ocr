print(f"[DEBUG] Loaded parser.py from: {__file__}, module: {__name__}")
# backend/parser.py
import re
from datetime import datetime

def try_parse_date(token):
    """Try several date formats; return DD-MM-YYYY or None."""
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(token, fmt)
            return dt.strftime("%d-%m-%Y")
        except Exception:
            continue
    # try contiguous 8 digits DDMMYYYY
    m = re.fullmatch(r"(\d{2})(\d{2})(\d{4})", token)
    if m:
        d, mo, y = m.groups()
        try:
            return datetime(int(y), int(mo), int(d)).strftime("%d-%m-%Y")
        except Exception:
            return None
    return None

def parse_receipt_text(ocr_text: str) -> dict:
    """
    Lightweight parser for receipts/vouchers.
    Returns a dict with keys: voucher_no, voucher_date, supplier_code, total_qty, gross_total, total_deductions, net_total, items (list)
    This is intentionally conservative — extend with more regex rules as needed.
    """
    text = ocr_text or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    data = {
        "voucher_no": None,
        "voucher_date": None,
        "supplier_code": None,
        "total_qty": 0,
        "gross_total": None,
        "total_deductions": None,
        "net_total": None,
        "items": []
    }

    # Voucher number patterns
    for ln in lines:
        m = re.search(r"(?:Voucher|Vou|Vouch|V)\s*(?:No\.?|Number|#)?\s*[:\-]?\s*(\d{1,8})", ln, re.IGNORECASE)
        if m:
            data["voucher_no"] = m.group(1)
            break

    # Date patterns
    for ln in lines:
        m = re.search(r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})", ln)
        if m:
            parsed = try_parse_date(m.group(1))
            if parsed:
                data["voucher_date"] = parsed
                break

    # Supplier code: find single-letter codes like 'A' or short tokens following 'Supplier' or 'Supp'
    for ln in lines:
        m = re.search(r"(?:Supplier|Supp|Supp\.?)\s*(?:Code|:)?\s*([A-Za-z0-9\-]{1,8})", ln, re.IGNORECASE)
        if m:
            data["supplier_code"] = m.group(1)
            break

    # Items: look for lines with qty price amount or qty x price = amount
    for ln in lines:
        m = re.match(r"^\s*(\d{1,4})\s*(?:x|X)?\s*([0-9,]+(?:\.[0-9]{1,2})?)\s*(?:=|\s)\s*([0-9,]+(?:\.[0-9]{1,2})?)\s*$", ln)
        if m:
            qty = int(m.group(1))
            price = float(m.group(2).replace(",", ""))
            amount = float(m.group(3).replace(",", ""))
            data["items"].append({"qty": qty, "unit_price": price, "amount": amount})
            data["total_qty"] += qty

    # Totals / Deductions: search bottom lines
    for ln in reversed(lines[-12:]):  # check last 12 lines first
        gm = re.search(r"(?:Grand\s+Total|Grand Total|Total Amount|Net Total|Net Amount)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", ln, re.IGNORECASE)
        if gm and data["net_total"] is None:
            data["net_total"] = float(gm.group(1).replace(",", ""))
        gm2 = re.search(r"(?:Gross\s+Total|Gross Total|Total)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", ln, re.IGNORECASE)
        if gm2 and data["gross_total"] is None:
            data["gross_total"] = float(gm2.group(1).replace(",", ""))
        # deductions keywords
        dm = re.search(r"(?:Commission|Damages|UnLoading|Unloading|LF\s*&\s*Cash|L/F)\s*[:\-]?\s*([0-9,]+(?:\.[0-9]{1,2})?)", ln, re.IGNORECASE)
        if dm:
            val = float(dm.group(1).replace(",", ""))
            if data["total_deductions"] is None:
                data["total_deductions"] = val
            else:
                data["total_deductions"] += val

    # If gross_total is None but items exist, sum them
    if data["gross_total"] is None and data["items"]:
        sg = sum(it["amount"] for it in data["items"])
        data["gross_total"] = round(sg, 2)

    # If net_total missing, compute from gross - deductions where possible
    if data["net_total"] is None:
        if data["gross_total"] is not None and data["total_deductions"] is not None:
            data["net_total"] = round(data["gross_total"] - data["total_deductions"], 2)

    # defaults: supplier_code 'A' if none (as per your earlier request)
    if not data["supplier_code"]:
        data["supplier_code"] = "A"

    return data
