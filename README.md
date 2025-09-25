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

## Google Colab setup

To explore the quotation tool inside Google Colab, run the following cells in
order. Replace `YOUR_GITHUB_USERNAME` with the actual account (or organisation)
that hosts the repository before executing the first command. Leaving the angle
brackets in place causes the shell to look for a file called
`YOUR_GITHUB_USERNAME`, which triggers the "No such file or directory"
message shown in the screenshot.

**Cell 1 – Clone the repository**

```python
repo_url = input("Enter the HTTPS clone URL of your paint-assistant repository: ").strip()
!git clone "$repo_url"
%cd paint-assistant
```

When prompted, paste the full HTTPS address of the repository you want to use
and press Enter (for example,
`https://github.com/your-company/paint-assistant.git`). This avoids the
"could not read Username" error that appears when a placeholder URL is left
unchanged. If the project is private, supply a Personal Access Token as part of
the URL, such as `https://<TOKEN>@github.com/your-company/paint-assistant.git`.

**Cell 2 – Install dependencies (plus pyngrok for tunnelling)**

```python
!pip install -q -r requirements.txt pyngrok
```

**Cell 3 – (Optional) run tests**

```python
!pytest
```

**Cell 4 – Configure Streamlit for Colab**

```python
import os

os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["STREAMLIT_SERVER_PORT"] = "8501"
os.environ["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
```

**Cell 5 – Launch the Streamlit app**

```python
!streamlit run app/streamlit_app.py &>/dev/null &
```

**Cell 6 – (First time only) authenticate ngrok**

```python
from getpass import getpass
from pyngrok import ngrok

authtoken = getpass("Paste your ngrok authtoken (visit dashboard.ngrok.com to generate one): ").strip()
if authtoken:
    ngrok.set_auth_token(authtoken)
```

You must sign up for a free ngrok account and supply the personal authtoken
displayed at <https://dashboard.ngrok.com/get-started/your-authtoken>. Without
it, ngrok returns the `ERR_NGROK_4018` authentication error shown in Colab.

**Cell 7 – Open an ngrok tunnel and display the public URL**

```python
public_url = ngrok.connect(8501, "http")
public_url
```

Visit the returned link to interact with the quotation builder. When you are
finished, disconnect the tunnel and stop Streamlit:

```python
ngrok.disconnect(public_url.public_url)
!killall streamlit
```

## Command-line quotation tool

If you prefer working in the terminal, run the interactive helper:

```bash
python quotation_tool.py
```

The script lets you type a product name to receive Google-style suggestions,
choose the pack size (drum, gallon, litre, etc.), apply an optional discount,
and automatically calculates the subtotal, VAT (5%), and grand total for the
quotation.
