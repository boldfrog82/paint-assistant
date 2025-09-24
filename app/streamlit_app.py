Replace the following two files with the exact code below.

# ================================
# FILE: app/core/quote.py
# ================================
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Tuple
import json

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PRODUCTS_PATH = DATA_DIR / "paint_products.json"
PRICES_PATH = DATA_DIR / "pricelistnationalpaints.json"

AED = Decimal("0.01")
VAT_RATE = Decimal("0.05")

def money(x: Decimal) -> Decimal:
    return x.quantize(AED, rounding=ROUND_HALF_UP)

def format_aed(x: Decimal) -> str:
    return f"AED {money(x):,.2f}"

def load_products(path: Path = PRODUCTS_PATH) -> Dict[str, dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    # Expect entries with keys: product_id, name, packs
    return {row["product_id"]: row for row in data}

def load_prices(path: Path = PRICES_PATH) -> Dict[Tuple[str, str], Decimal]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    # Expect entries with keys: product_id, pack, price_aed
    idx: Dict[Tuple[str, str], Decimal] = {}
    for row in data:
        idx[(row["product_id"], row["pack"])] = Decimal(str(row["price_aed"]))
    return idx

def search_products(products: Dict[str, dict], q: str, limit: int = 20) -> List[dict]:
    qn = (q or "").strip().lower()
    if not qn:
        # return first N products deterministically
        return sorted(products.values(), key=lambda r: r["name"])[:limit]
    scored = []
    for p in products.values():
        name = p["name"].lower()
        score = 0
        if name.startswith(qn): score += 3
        if qn in name:         score += 2
        if score: scored.append((score, p))
    scored.sort(key=lambda t: (-t[0], t[1]["name"]))
    return [p for _, p in scored[:limit]]

@dataclass
class QuoteItem:
    product_id: str
    product_name: str
    pack: str
    unit_price: Decimal
    qty: int
    discount_pct: Decimal  # 0..100

    @property
    def line_net(self) -> Decimal:
        gross = self.unit_price * self.qty
        disc = gross * self.discount_pct / Decimal("100")
        return money(gross - disc)

def make_item(products: Dict[str, dict], prices: Dict[Tuple[str,str], Decimal],
              product_id: str, pack: str, qty: int, discount_pct: Decimal) -> QuoteItem:
    prod = products.get(product_id)
    if not prod:
        raise KeyError("Unknown product_id")
    price = prices.get((product_id, pack))
    if price is None:
        raise KeyError("No price for selected pack")
    return QuoteItem(
        product_id=product_id,
        product_name=prod["name"],
        pack=pack,
        unit_price=Decimal(str(price)),
        qty=int(qty),
        discount_pct=Decimal(str(discount_pct or 0)),
    )

def compute_totals(items: List[QuoteItem]) -> dict:
    subtotal = sum((it.line_net for it in items), Decimal("0"))
    subtotal = money(subtotal)
    vat = money(subtotal * VAT_RATE)
    total = money(subtotal + vat)
    return {"subtotal": subtotal, "vat": vat, "total": total}


# ================================
# FILE: app/streamlit_app.py
# ================================
from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st

# reportlab imports (top-level, not mid-file)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.core.quote import (
    load_products,
    load_prices,
    search_products,
    make_item,
    compute_totals,
    format_aed,
    QuoteItem,
)

st.set_page_config(page_title="Paint Quotation Generator", page_icon="🎨", layout="wide")

# Load catalogs once and cache
@st.cache_data
def get_catalogs():
    products = load_products()
    prices = load_prices()
    return products, prices

PRODUCTS, PRICES = get_catalogs()

def build_pdf(customer: dict, items: List[QuoteItem], totals: dict) -> bytes:
    """Generate a simple A4 PDF invoice."""
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    left = 20 * mm
    y = height - 25 * mm

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(left, y, "Paint Quotation")
    y -= 18

    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, y, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    y -= 14

    # Customer block
    if customer.get("name"):
        pdf.drawString(left, y, f"Customer: {customer['name']}")
        y -= 12
    if customer.get("phone"):
        pdf.drawString(left, y, f"Phone: {customer['phone']}")
        y -= 12
    if customer.get("notes"):
        pdf.drawString(left, y, "Notes:")
        y -= 12
        for line in str(customer["notes"]).splitlines():
            pdf.drawString(left + 8 * mm, y, line[:100])
            y -= 12

    # Table headers
    y -= 8
    headers = ["Product", "Pack", "Qty", "Unit", "Disc %", "Line Net"]
    cols = [left, left + 70 * mm, left + 110 * mm, left + 135 * mm, left + 160 * mm, left + 190 * mm]

    pdf.setFont("Helvetica-Bold", 10)
    for x, h in zip(cols, headers):
        pdf.drawString(x, y, h)
    y -= 12
    pdf.line(left, y + 4, cols[-1] + 25 * mm, y + 4)

    # Rows
    pdf.setFont("Helvetica", 10)
    for it in items:
        if y < 40 * mm:  # new page
            pdf.showPage()
            y = height - 25 * mm
            pdf.setFont("Helvetica-Bold", 10)
            for x, h in zip(cols, headers):
                pdf.drawString(x, y, h)
            y -= 12
            pdf.line(left, y + 4, cols[-1] + 25 * mm, y + 4)
            pdf.setFont("Helvetica", 10)

        pdf.drawString(cols[0], y, it.product_name[:40])
        pdf.drawString(cols[1], y, it.pack)
        pdf.drawRightString(cols[2] + 8 * mm, y, f"{it.qty}")
        pdf.drawRightString(cols[3] + 18 * mm, y, format_aed(it.unit_price))
        pdf.drawRightString(cols[4] + 12 * mm, y, f"{it.discount_pct.normalize()}%")
        pdf.drawRightString(cols[5] + 25 * mm, y, format_aed(it.line_net))
        y -= 12

    # Totals
    y -= 10
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawRightString(cols[5] + 25 * mm, y, f"Subtotal: {format_aed(totals['subtotal'])}")
    y -= 14
    pdf.drawRightString(cols[5] + 25 * mm, y, f"VAT (5%): {format_aed(totals['vat'])}")
    y -= 14
    pdf.drawRightString(cols[5] + 25 * mm, y, f"Total: {format_aed(totals['total'])}")

    pdf.showPage()
    pdf.save()
    buf.seek(0)
    return buf.read()

# ---- UI ----
if "items" not in st.session_state:
    st.session_state["items"] = []  # List[QuoteItem]

with st.sidebar:
    st.header("Customer")
    cust_name = st.text_input("Name")
    cust_phone = st.text_input("Phone")
    cust_notes = st.text_area("Notes")

st.title("🎨 Paint Quotation Builder")

# Search + select
q = st.text_input("Search products", placeholder="Type a product name…")
matches = search_products(PRODUCTS, q, limit=20)
if not matches:
    st.info("No products match your search.")
    packs = []
    selected = None
else:
    names = [f"{p['name']} — {p['product_id']}" for p in matches]
    selected_label = st.selectbox("Product", names)
    selected_id = selected_label.split(" — ")[-1]
    selected = PRODUCTS[selected_id]
    packs = selected.get("packs", [])

pack = st.selectbox("Pack", packs) if packs else None
qty = st.number_input("Quantity", min_value=1, value=1, step=1)
disc = st.number_input("Line discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)

if st.button("Add to quote", type="primary", use_container_width=True):
    if not selected or not pack:
        st.error("Select a product and pack first.")
    else:
        try:
            item = make_item(PRODUCTS, PRICES, selected["product_id"], pack, qty, Decimal(str(disc)))
            st.session_state["items"].append(item)
            st.success(f"Added {item.product_name} — {item.pack}")
        except KeyError as e:
            st.error(str(e))

items: List[QuoteItem] = st.session_state["items"]

with st.expander("Current quote", expanded=True):
    if items:
        rows = [{
            "Product": it.product_name,
            "Pack": it.pack,
            "Qty": it.qty,
            "Unit Price": format_aed(it.unit_price),
            "Disc %": f"{it.discount_pct.normalize()}%",
            "Line Net": format_aed(it.line_net),
        } for it in items]
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        totals = compute_totals(items)
        c1, c2, c3 = st.columns(3)
        c1.metric("Subtotal", format_aed(totals["subtotal"]))
        c2.metric("VAT 5%", format_aed(totals["vat"]))
        c3.metric("Total", format_aed(totals["total"]))

        # CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "paint-quotation.csv", "text/csv", use_container_width=True)

        # PDF
        pdf_bytes = build_pdf({"name": cust_name, "phone": cust_phone, "notes": cust_notes}, items, totals)
        st.download_button("Export PDF", pdf_bytes, "paint-quotation.pdf", "application/pdf", use_container_width=True)

        if st.button("Clear quote", use_container_width=True):
            st.session_state["items"] = []
            st.experimental_rerun()
    else:
        st.caption("Add products to start a quotation.")
