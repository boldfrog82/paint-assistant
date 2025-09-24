"""Minimal Streamlit UI for building customer paint quotations."""

from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal
from typing import List

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.core.quote import (
    compute_totals,
    find_matching_products,
    format_aed,
    load_price_catalog,
    load_products,
    quote_row,
)

st.set_page_config(page_title="Paint Quotation", page_icon="🎨", layout="wide")


@st.cache_data
def get_catalogs() -> tuple[List[dict], dict[str, dict[str, Decimal]]]:
    products = load_products()
    prices = load_price_catalog()
    return products, prices


PRODUCTS, PRICE_CATALOG = get_catalogs()

def _format_decimal(value: Decimal, digits: int | None = None) -> str:
    """Render a ``Decimal`` without scientific notation."""

    fmt = f".{digits}f" if digits is not None else "f"
    text = format(value, fmt)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def build_pdf(
    customer: dict,
    items: List[dict],
    subtotal: Decimal,
    vat: Decimal,
    total: Decimal,
) -> bytes:
    """Create a simple PDF invoice for the current quotation."""

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin_x = 20 * mm
    y = height - 25 * mm

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin_x, y, "Paint Quotation")
    y -= 18

    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin_x, y, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    y -= 14

    if customer.get("name"):
        pdf.drawString(margin_x, y, f"Customer: {customer['name']}")
        y -= 12
    if customer.get("phone"):
        pdf.drawString(margin_x, y, f"Phone: {customer['phone']}")
        y -= 12
    if customer.get("notes"):
        pdf.drawString(margin_x, y, "Notes:")
        y -= 12
        for line in customer["notes"].splitlines():
            pdf.drawString(margin_x + 6 * mm, y, line)
            y -= 12

    y -= 6
    headers = ["Product", "Pack", "Qty", "Unit Price", "Disc %", "Line Net"]
    col_positions = [margin_x, margin_x + 70 * mm, margin_x + 115 * mm,
                     margin_x + 140 * mm, margin_x + 165 * mm, margin_x + 195 * mm]

    def _draw_header(current_y: float) -> float:
        pdf.setFont("Helvetica-Bold", 10)
        for x, header in zip(col_positions, headers):
            pdf.drawString(x, current_y, header)
        return current_y - 14

    def _draw_row(current_y: float, item: dict) -> float:
        pdf.setFont("Helvetica", 10)
        pdf.drawString(col_positions[0], current_y, item["product_name"])
        pdf.drawString(col_positions[1], current_y, item["pack"])
        pdf.drawRightString(col_positions[2] + 8 * mm, current_y, _format_decimal(item["quantity"]))
        pdf.drawRightString(col_positions[3] + 20 * mm, current_y, format_aed(item["unit_price"]))
        pdf.drawRightString(
            col_positions[4] + 12 * mm, current_y, f"{_format_decimal(item['discount_pct'])}%"
        )
        pdf.drawRightString(col_positions[5] + 25 * mm, current_y, format_aed(item["line_net"]))
        return current_y - 14

    y = _draw_header(y)
    for item in items:
        if y < 40 * mm:
            pdf.showPage()
            y = height - 25 * mm
            y = _draw_header(y)
        y = _draw_row(y, item)

    y -= 12
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawRightString(col_positions[5] + 25 * mm, y, f"Subtotal: {format_aed(subtotal)}")
    y -= 14
    pdf.drawRightString(col_positions[5] + 25 * mm, y, f"VAT (5%): {format_aed(vat)}")
    y -= 14
    pdf.drawRightString(col_positions[5] + 25 * mm, y, f"Total: {format_aed(total)}")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.read()


if "items" not in st.session_state:
    st.session_state["items"] = []

st.sidebar.header("Customer details")
customer_name = st.sidebar.text_input("Name")
customer_phone = st.sidebar.text_input("Phone")
customer_notes = st.sidebar.text_area("Notes")

st.title("Paint quotation builder")

search_query = st.text_input("Search products", placeholder="Type to search the catalogue")
matched_products = find_matching_products(search_query) if search_query else find_matching_products("")
product_names = [product.get("product_name", "") for product in matched_products if product.get("product_name")]

selected_product = None
if product_names:
    selected_product = st.selectbox("Product", product_names)
else:
    st.info("No products match the current search.")

if selected_product:
    pack_options = PRICE_CATALOG.get(selected_product, {})
    packs = list(pack_options.keys())
    if packs:
        pack_choice = st.selectbox("Pack", packs)
        quantity_value = st.number_input("Quantity", min_value=1, value=1, step=1)
        discount_value = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)

        if st.button("Add to Quote", type="primary"):
            try:
                item = quote_row(selected_product, pack_choice, quantity_value, discount_value)
            except (KeyError, ValueError) as exc:
                st.error(str(exc))
            else:
                st.session_state["items"].append(item)
                st.success(f"Added {selected_product} — {pack_choice}")
    else:
        st.warning("No pricing data is available for the selected product.")

items = st.session_state["items"]

with st.expander("Current quotation", expanded=bool(items)):
    if items:
        table_rows = [
            {
                "Product": item["product_name"],
                "Pack": item["pack"],
                "Qty": _format_decimal(item["quantity"]),
                "Unit Price": format_aed(item["unit_price"]),
                "Disc %": f"{_format_decimal(item['discount_pct'])}%",
                "Line Net": format_aed(item["line_net"]),
            }
            for item in items
        ]
        table_df = pd.DataFrame(table_rows)
        st.dataframe(table_df, hide_index=True, use_container_width=True)

        subtotal, vat, total = compute_totals(items)
        col1, col2, col3 = st.columns(3)
        col1.metric("Subtotal", format_aed(subtotal))
        col2.metric("VAT 5%", format_aed(vat))
        col3.metric("Total", format_aed(total))

        csv_rows = [
            {
                "product_id": item["product_id"],
                "product_name": item["product_name"],
                "pack": item["pack"],
                "quantity": _format_decimal(item["quantity"]),
                "unit_price": format(item["unit_price"], ".2f"),
                "discount_pct": _format_decimal(item["discount_pct"]),
                "line_net": format(item["line_net"], ".2f"),
            }
            for item in items
        ]
        csv_df = pd.DataFrame(csv_rows)
        csv_data = csv_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            data=csv_data,
            file_name="paint-quotation.csv",
            mime="text/csv",
            use_container_width=True,
        )

        pdf_bytes = build_pdf(
            {"name": customer_name, "phone": customer_phone, "notes": customer_notes},
            items,
            subtotal,
            vat,
            total,
        )
        st.download_button(
            "Export PDF",
            data=pdf_bytes,
            file_name="paint-quotation.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        if st.button("Clear quote"):
            st.session_state["items"] = []
            st.experimental_rerun()
    else:
        st.caption("Add products to start building a quotation.")
