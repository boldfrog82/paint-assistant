"""Streamlit user interface for the paint quotation generator."""

from __future__ import annotations

import io
from decimal import Decimal
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.quote import (
    QuoteItem,
    calculate_subtotal,
    calculate_total,
    calculate_vat,
    format_aed,
    load_price_catalog,
    load_products,
    search_products,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PRODUCTS_PATH = DATA_DIR / "paint_products.json"
PRICES_PATH = DATA_DIR / "pricelistnationalpaints.json"

st.set_page_config(page_title="Paint Quotation Generator", page_icon="🎨", layout="wide")


@st.cache_data
def get_catalogs() -> tuple[List[dict], dict[str, List[dict]]]:
    products = load_products(PRODUCTS_PATH)
    price_catalog = load_price_catalog(PRICES_PATH)
    return products, price_catalog


def build_pdf(
    customer: dict,
    quote_items: List[QuoteItem],
    subtotal: Decimal,
    vat: Decimal,
    total: Decimal,
) -> bytes:
    """Create a simple PDF invoice using reportlab."""

    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title="Paint Quotation")
    styles = getSampleStyleSheet()

    elements = [Paragraph("Paint Quotation", styles["Title"]), Spacer(1, 12)]

    customer_lines = [customer.get("name") or "Unnamed Customer"]
    if customer.get("phone"):
        customer_lines.append(f"Phone: {customer['phone']}")
    if customer.get("notes"):
        customer_lines.append(f"Notes: {customer['notes']}")

    elements.append(Paragraph("<br/>".join(customer_lines), styles["Normal"]))
    elements.append(Spacer(1, 12))

    table_data = [["Product", "Pack Size", "Qty", "Unit Price", "Discount %", "Line Total"]]
    for item in quote_items:
        table_data.append(
            [
                item.product_name,
                item.pack_size,
                f"{item.quantity}",
                format_aed(item.unit_price),
                f"{item.discount_pct.normalize()}%" if item.discount_pct else "0%",
                format_aed(item.line_total),
            ]
        )

    quote_table = Table(table_data, hAlign="LEFT")
    quote_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ]
        )
    )
    elements.extend([quote_table, Spacer(1, 12)])

    totals_data = [
        ["Subtotal", format_aed(subtotal)],
        ["VAT (5%)", format_aed(vat)],
        ["Total", format_aed(total)],
    ]
    totals_table = Table(totals_data, hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 12),
            ]
        )
    )
    elements.append(totals_table)

    document.build(elements)
    buffer.seek(0)
    return buffer.read()


products, price_catalog = get_catalogs()
product_lookup = {product.get("product_name", ""): product for product in products}

if "quote_items" not in st.session_state:
    st.session_state.quote_items = []

st.sidebar.header("Customer information")
customer_name = st.sidebar.text_input("Customer name", placeholder="Jane Doe")
customer_phone = st.sidebar.text_input("Phone number", placeholder="050-123-4567")
customer_notes = st.sidebar.text_area("Notes", placeholder="Preferred delivery time, site details, etc.")

st.title("Build a quotation")

search_query = st.text_input("Search for products", placeholder="Start typing a product name...")
matched_products = search_products(products, search_query, limit=15) if search_query else products[:15]
product_options = [item.get("product_name", "") for item in matched_products if item.get("product_name")]

if product_options:
    selected_product_name = st.selectbox("Select a product", product_options)
else:
    selected_product_name = None
    st.info("No products match your search. Try another term.")

if selected_product_name:
    product_details = product_lookup.get(selected_product_name, {})
    st.markdown(f"**Selected:** {selected_product_name}")
    if description := product_details.get("description"):
        st.write(description)

    pack_options = price_catalog.get(selected_product_name, [])
    pack_labels = [option["size"] for option in pack_options]

    if pack_options:
        selected_pack = st.selectbox("Pack size", pack_labels)
        price_map = {option["size"]: option["price"] for option in pack_options}
        unit_price = price_map[selected_pack]
        quantity_value = st.number_input("Quantity", min_value=1, value=1, step=1, format="%d")
        discount_value = st.number_input("Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)

        if st.button("Add to quote", use_container_width=True):
            st.session_state.quote_items.append(
                QuoteItem(
                    product_name=selected_product_name,
                    pack_size=selected_pack,
                    quantity=Decimal(str(quantity_value)),
                    unit_price=unit_price,
                    discount_pct=Decimal(str(discount_value)),
                )
            )
            st.success(f"Added {selected_product_name} - {selected_pack} to the quote.")
    else:
        st.warning("No price information is available for this product.")

with st.expander("Current quote", expanded=True):
    quote_items: List[QuoteItem] = st.session_state.quote_items
    if quote_items:
        line_totals = [item.line_total for item in quote_items]
        subtotal = calculate_subtotal(line_totals)
        vat = calculate_vat(subtotal)
        total = calculate_total(subtotal, vat)

        table_rows = [
            {
                "Product": item.product_name,
                "Pack Size": item.pack_size,
                "Quantity": f"{item.quantity}",
                "Unit Price": format_aed(item.unit_price),
                "Discount %": f"{item.discount_pct.normalize()}%" if item.discount_pct else "0%",
                "Line Total": format_aed(item.line_total),
            }
            for item in quote_items
        ]
        table_df = pd.DataFrame(table_rows)
        st.dataframe(table_df, hide_index=True, use_container_width=True)

        totals_col1, totals_col2, totals_col3 = st.columns(3)
        totals_col1.metric("Subtotal", format_aed(subtotal))
        totals_col2.metric("VAT (5%)", format_aed(vat))
        totals_col3.metric("Total", format_aed(total))

        csv_data = table_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            csv_data,
            file_name="paint-quotation.csv",
            mime="text/csv",
            use_container_width=True,
        )

        pdf_bytes = build_pdf(
            {"name": customer_name, "phone": customer_phone, "notes": customer_notes},
            quote_items,
            subtotal,
            vat,
            total,
        )
        st.download_button(
            "Export to PDF",
            data=pdf_bytes,
            file_name="paint-quotation.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        if st.button("Clear quote", use_container_width=True):
            st.session_state.quote_items = []
            st.experimental_rerun()
    else:
        st.caption("Add items to build your quotation.")
