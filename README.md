# paint-assistant

Tools and datasets for exploring National Paints products.

## Running the ASGI API

The project exposes the chatbot through a small FastAPI application. Install
the runtime dependencies and launch the ASGI server with

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The server provides two endpoints:

- `GET /health` – simple health check that returns `{"status": "ok"}` when the
  service is ready.
- `POST /chat` – accepts a JSON body with a `prompt` field and returns the
  chatbot's response as `{"response": "..."}`.
- `POST /ai/chat` – enhanced assistant that supplements answers with retrieval
  and tool data.

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

## AI-powered chat endpoint

The `/ai/chat` endpoint combines retrieval-augmented context with price and
product lookup tools before handing the prompt to an LLM. To try it locally:

1. Install dependencies listed in `requirements.txt`.
2. Build the retrieval index:

   ```bash
   python -m src.rag.build_index
   ```

3. Export your OpenAI API key so the LLM backend can authenticate:

   ```bash
   export OPENAI_API_KEY="sk-your-api-key"
   ```

4. Start Uvicorn as shown above and issue a request:

   ```bash
   curl -X POST "http://127.0.0.1:8000/ai/chat" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "How much is A119 in 18 Ltr (Drum)?"}'
   ```

   The response includes the model's reply, tool payloads, and retrieved
   passages used to craft the answer.

## Running tests

The project uses [pytest](https://docs.pytest.org/) for automated testing. To
run the test suite, install the project's Python dependencies (if any) and
execute the legacy tests with:

```bash
pytest tests
```

To exercise both the legacy checks and the AI chat scenarios run:

```bash
pytest tests tests_ai
```

The tests cover JSON loading helpers, validation utilities for detecting
duplicate product codes, and integration points for the AI-powered endpoint.
