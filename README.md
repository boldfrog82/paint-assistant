# Paint Quotation Generator

An interactive Streamlit application for building customer quotations using the National Paints product catalogue and price list. The tool lets sales teams search the catalogue, add products with pack sizes, apply optional discounts, and export quotations as CSV or PDF files. Totals automatically include the mandatory 5% VAT.

## Getting started

1. **Install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the Streamlit app**
   ```bash
   streamlit run app/streamlit_app.py
   ```
   The interface opens in your browser. Use the sidebar to enter customer details, search for paint products, and add them to the quotation.

## Data files

The app reads two JSON datasets stored in the `data/` directory:

- `paint_products.json` – descriptive product catalogue.
- `pricelistnationalpaints.json` – pricing information grouped by category.

When updating these files, validate them against their JSON Schemas to avoid runtime errors:

```bash
python scripts/validate_data.py
```

Both schema definitions live in `schemas/`.

## Testing

Run unit tests to verify the quotation maths:

```bash
pytest
```

## Project structure

```
app/
├── core/quote.py          # Quotation logic and helpers
└── streamlit_app.py       # Streamlit user interface

data/                     # Product and price data sources
schemas/                   # JSON Schemas for validation
scripts/validate_data.py   # Data validation helper
tests/test_quote.py        # Pytest suite
```

## Web UI (Streamlit)

Launch the quotation interface locally with:

```bash
streamlit run app/streamlit_app.py
```

The browser UI lets you:

- search the catalogue with instant suggestions and select the right pack size
- enter quantities and optional discounts for each line item
- review running subtotals with 5% VAT automatically applied
- download the current quotation as CSV or export a simple PDF invoice
