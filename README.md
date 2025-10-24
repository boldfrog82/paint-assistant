# Paint Assistant Chatbot

This project provides a FastAPI service that serves as a grounded chatbot for National Paints product and price information. It indexes the provided JSON documents and answers questions about product details and pricing without hallucinations.

## Prerequisites

* Python 3.10+
* `paint_products.json` and `pricelistnationalpaints.json` must be present in the project root.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the API

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### Health Check

```
GET http://localhost:8000/health
```

### Chat Endpoint

```
POST http://localhost:8000/chat
Content-Type: application/json
{
  "message": "What is the price of National N.C. Sanding Sealer in 3.6 Ltr?",
  "confidence_threshold": 70
}
```

The response contains structured product matches, pricing, and metadata sourced from the uploaded files.

## Development

To restart automatically when files change, run the module directly:

```bash
python app.py
```

This uses Uvicorn's reload mode for local development.
