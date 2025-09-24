codex/create-product-quotation-tool-chfqn1

codex/create-product-quotation-tool-db0tm4
Codex
"""Minimal Streamlit UI for building customer paint quotations."""

from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal
codex/create-product-quotation-tool-chfqn1


codex/create-product-quotation-tool-nq6b3b
"""Minimal Streamlit UI for building customer paint quotations."""

"""Streamlit user interface for the paint quotation generator."""
Codex

from __future__ import annotations

import io
codex/create-product-quotation-tool-nq6b3b
from datetime import datetime
from decimal import Decimal

from decimal import Decimal
from pathlib import Path
Codex
Codex
Codex
from typing import List

import pandas as pd
import streamlit as st
codex/create-product-quotation-tool-chfqn1

codex/create-product-quotation-tool-db0tm4

codex/create-product-quotation-tool-nq6b3b
Codex
Codex
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

codex/create-product-quotation-tool-chfqn1

def build_pdf(
    customer: dict,
    items: List[dict],

codex/create-product-quotation-tool-db0tm4

def build_pdf(
    customer: dict,
    items: List[dict],

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
Codex


def build_pdf(
    customer: dict,
codex/create-product-quotation-tool-nq6b3b
    items: List[dict],

    quote_items: List[QuoteItem],
Codex
Codex
Codex
    subtotal: Decimal,
    vat: Decimal,
    total: Decimal,
) -> bytes:
codex/create-product-quotation-tool-chfqn1

codex/create-product-quotation-tool-db0tm4

codex/create-product-quotation-tool-nq6b3b
Codex
Codex
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
codex/create-product-quotation-tool-chfqn1

codex/create-product-quotation-tool-db0tm4


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
Codex
Codex
Codex
    buffer.seek(0)
    return buffer.read()


codex/create-product-quotation-tool-chfqn1

codex/create-product-quotation-tool-db0tm4

codex/create-product-quotation-tool-nq6b3b
Codex
Codex
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
codex/create-product-quotation-tool-chfqn1

codex/create-product-quotation-tool-db0tm4


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
Codex
Codex
Codex
        ]
        table_df = pd.DataFrame(table_rows)
        st.dataframe(table_df, hide_index=True, use_container_width=True)

codex/create-product-quotation-tool-chfqn1

codex/create-product-quotation-tool-db0tm4

codex/create-product-quotation-tool-nq6b3b
Codex
Codex
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
codex/create-product-quotation-tool-chfqn1

codex/create-product-quotation-tool-db0tm4


        totals_col1, totals_col2, totals_col3 = st.columns(3)
        totals_col1.metric("Subtotal", format_aed(subtotal))
        totals_col2.metric("VAT (5%)", format_aed(vat))
        totals_col3.metric("Total", format_aed(total))

        csv_data = table_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download CSV",
            csv_data,
Codex
Codex
Codex
            file_name="paint-quotation.csv",
            mime="text/csv",
            use_container_width=True,
        )

        pdf_bytes = build_pdf(
            {"name": customer_name, "phone": customer_phone, "notes": customer_notes},
codex/create-product-quotation-tool-chfqn1
            items,

codex/create-product-quotation-tool-db0tm4
            items,

codex/create-product-quotation-tool-nq6b3b
            items,

            quote_items,
Codex
Codex
Codex
            subtotal,
            vat,
            total,
        )
        st.download_button(
codex/create-product-quotation-tool-chfqn1
            "Export PDF",

codex/create-product-quotation-tool-db0tm4
            "Export PDF",

codex/create-product-quotation-tool-nq6b3b
            "Export PDF",

            "Export to PDF",
Codex
Codex
Codex
            data=pdf_bytes,
            file_name="paint-quotation.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

codex/create-product-quotation-tool-chfqn1

codex/create-product-quotation-tool-db0tm4

codex/create-product-quotation-tool-nq6b3b
Codex
Codex
        if st.button("Clear quote"):
            st.session_state["items"] = []
            st.experimental_rerun()
    else:
        st.caption("Add products to start building a quotation.")
codex/create-product-quotation-tool-chfqn1

codex/create-product-quotation-tool-db0tm4


        if st.button("Clear quote", use_container_width=True):
            st.session_state.quote_items = []
            st.experimental_rerun()
    else:
        st.caption("Add items to build your quotation.")
Codex
Codex
Codex
