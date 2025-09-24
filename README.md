# paint-assistant

This repository contains supporting data for National Paints products together
with a lightweight interactive quotation builder.

## Quotation Builder

Run the tool from the repository root:

```
python quotation_tool.py
```

Features:

- Type part of a product name and receive instant suggestions similar to a
  search engine auto-complete.
- Choose the desired pack size (drum, gallon, litre, etc.) and quantity.
- Apply an optional per-line discount before VAT.
- Automatically calculates the subtotal, total discount, VAT (5%), and the
  grand total for the quotation.

The script reads prices from `pricelistnationalpaints.json`, so keep that file
up to date to reflect the latest pricing.
