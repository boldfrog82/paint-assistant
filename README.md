# paint-assistant

Tools and datasets for exploring National Paints products.

## Running the ASGI API

The project exposes the chatbot through a small FastAPI application. Install
the runtime dependencies and launch the ASGI server with

```bash
pip install fastapi uvicorn
uvicorn app.main:app --reload
```

The server provides two endpoints:

- `GET /health` – simple health check that returns `{"status": "ok"}` when the
  service is ready.
- `POST /chat` – accepts a JSON body with a `prompt` field and returns the
  chatbot's response as `{"response": "..."}`.

Example usage with `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Tell me about NP Colorant"}'
```

The response will contain the assistant's answer:

```json
{"response": "NP Colorant..."}
```

## Running tests

The project uses [pytest](https://docs.pytest.org/) for automated testing. To
run the test suite, install the project's Python dependencies (if any) and
execute:

```bash
pytest
```

The tests exercise the JSON loading helpers and the validation utilities for
detecting duplicate product codes.
