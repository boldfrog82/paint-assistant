import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from rapidfuzz import process, fuzz

# -----------------------------
# Utilities
# -----------------------------

def normalize_name(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s\-\&/.:()]+", "", s)
    return s


def is_like_price_query(text: str) -> bool:
    t = text.lower()
    price_terms = [
        "price",
        "cost",
        "how much",
        "aed",
        "dirham",
        "quote",
        "quotation",
        "rate",
        "per liter",
        "per litre",
        "drum price",
        "gallon price",
        "tin price",
        "kg price",
        "price of",
        "pricing",
    ]
    return any(term in t for term in price_terms)


def extract_size_hints(text: str) -> List[str]:
    # Heuristic to pick likely size mentions from user query
    t = text.lower()
    patterns = [
        r"\b\d+(\.\d+)?\s*ltr\b",
        r"\b\d+(\.\d+)?\s*ltr[s]?\b",
        r"\b\d+(\.\d+)?\s*liter[s]?\b",
        r"\b\d+(\.\d+)?\s*litre[s]?\b",
        r"\b\d+(\.\d+)?\s*kg\b",
        r"\b\d+(\.\d+)?\s*kg[s]?\b",
        r"\bdrum\b",
        r"\bgallon\b",
        r"\btin\b",
        r"\bbarrel\b",
        r"\bbox\b",
    ]
    hints = set()
    for pat in patterns:
        for m in re.finditer(pat, t):
            hints.add(m.group(0))
    return sorted(hints)


def as_bullets(value: Any, indent: int = 0) -> List[str]:
    """Formats nested dicts/lists/strings as bullet lines."""
    prefix = "  " * indent + "- "
    lines: List[str] = []
    if value is None:
        return lines
    if isinstance(value, str):
        lines.append(prefix + value.strip())
    elif isinstance(value, (int, float, bool)):
        lines.append(prefix + str(value))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (str, int, float, bool)):
                lines.append(prefix + str(item))
            elif isinstance(item, dict):
                # one bullet with nested keys
                sublines = dict_to_lines(item, indent + 1)
                if sublines:
                    lines.append(prefix + "(item)")
                    lines.extend(sublines)
            else:
                lines.append(prefix + str(item))
    elif isinstance(value, dict):
        lines.extend(dict_to_lines(value, indent))
    else:
        lines.append(prefix + str(value))
    return lines


def dict_to_lines(d: Dict[str, Any], indent: int = 0) -> List[str]:
    lines: List[str] = []
    for k, v in d.items():
        label = k.replace("_", " ").strip()
        if isinstance(v, (str, int, float, bool)):
            lines.append(("  " * indent) + f"- {label}: {v}")
        elif isinstance(v, list):
            lines.append(("  " * indent) + f"- {label}:")
            for item in v:
                if isinstance(item, dict):
                    lines.extend(dict_to_lines(item, indent + 1))
                else:
                    lines.append(("  " * (indent + 1)) + f"- {item}")
        elif isinstance(v, dict):
            lines.append(("  " * indent) + f"- {label}:")
            lines.extend(dict_to_lines(v, indent + 1))
        elif v is None:
            continue
        else:
            lines.append(("  " * indent) + f"- {label}: {v}")
    return lines


# -----------------------------
# Data loading and indexing
# -----------------------------

PRODUCTS_FILE = Path("paint_products.json")
PRICES_FILE = Path("pricelistnationalpaints.json")


def collect_product_records(node: Any, bucket: List[Dict[str, Any]]):
    """Recursively traverse node to collect dicts that look like product records (have product_name)."""
    if isinstance(node, dict):
        if "product_name" in node and isinstance(node["product_name"], str):
            bucket.append(node)
        for v in node.values():
            collect_product_records(v, bucket)
    elif isinstance(node, list):
        for item in node:
            collect_product_records(item, bucket)


def flatten_price_list(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten all price products with context: category, subcategory."""
    out: List[Dict[str, Any]] = []
    categories = node.get("product_categories", []) or []
    for cat in categories:
        cat_name = cat.get("category_name")
        for sub in cat.get("subcategories", []) or []:
            sub_name = sub.get("subcategory_name")
            for p in sub.get("products", []) or []:
                rec = {
                    "category_name": cat_name,
                    "subcategory_name": sub_name,
                    "product_name": p.get("product_name"),
                    "product_code": p.get("product_code"),
                    "prices": p.get("prices", []),
                }
                out.append(rec)
    return out


class DataIndex:
    def __init__(self):
        self.products_list: List[Dict[str, Any]] = []
        self.prices_list: List[Dict[str, Any]] = []
        self.product_names: List[str] = []
        self.name_to_products: Dict[str, List[Dict[str, Any]]] = {}
        self.name_to_price_entries: Dict[str, List[Dict[str, Any]]] = {}
        self.code_to_price_entries: Dict[str, List[Dict[str, Any]]] = {}
        self.price_meta: Dict[str, Any] = {}

    def load(self):
        if not PRODUCTS_FILE.exists():
            raise FileNotFoundError(f"Missing required file: {PRODUCTS_FILE.name}")
        if not PRICES_FILE.exists():
            raise FileNotFoundError(f"Missing required file: {PRICES_FILE.name}")

        # Load and collect product records (handles nested arrays)
        products_raw = json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))
        bucket: List[Dict[str, Any]] = []
        collect_product_records(products_raw, bucket)
        self.products_list = bucket

        # Build product name indexes
        self.product_names = [p["product_name"] for p in self.products_list if "product_name" in p]
        for p in self.products_list:
            nm = normalize_name(p["product_name"])
            self.name_to_products.setdefault(nm, []).append(p)

        # Load and flatten prices
        prices_raw = json.loads(PRICES_FILE.read_text(encoding="utf-8"))
        self.price_meta = {
            "document_source": prices_raw.get("document_source"),
            "effective_date": prices_raw.get("effective_date"),
            "currency": prices_raw.get("currency"),
            "notes": prices_raw.get("notes"),
        }
        self.prices_list = flatten_price_list(prices_raw)
        # Build price indexes by name and code
        for r in self.prices_list:
            nm = r.get("product_name")
            if not nm:
                continue
            norm = normalize_name(nm)
            self.name_to_price_entries.setdefault(norm, []).append(r)
            code = r.get("product_code")
            if code:
                self.code_to_price_entries.setdefault(code.strip(), []).append(r)

    def match_product_names(self, query: str, limit: int = 5) -> List[Tuple[str, float]]:
        """Return [(product_name, score), ...] using fuzzy match over product names."""
        if not self.product_names:
            return []
        results = process.extract(
            query, self.product_names, scorer=fuzz.WRatio, limit=limit
        )
        # results: List[Tuple[str, score, idx]]
        return [(name, float(score)) for (name, score, _idx) in results]

    def get_products_by_name(self, product_name: str) -> List[Dict[str, Any]]:
        return self.name_to_products.get(normalize_name(product_name), [])

    def get_price_by_name(self, product_name: str) -> List[Dict[str, Any]]:
        return self.name_to_price_entries.get(normalize_name(product_name), [])

    def get_price_by_code(self, code: str) -> List[Dict[str, Any]]:
        return self.code_to_price_entries.get(code.strip(), [])


INDEX = DataIndex()
try:
    INDEX.load()
except Exception as e:
    # Fail fast with explicit message; FastAPI will raise 500 if used before files exist
    print(f"[Startup Warning] Data loading issue: {e}")


# -----------------------------
# API Models
# -----------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    top_k: int = Field(3, ge=1, le=10, description="Number of product candidates to consider")
    confidence_threshold: float = Field(
        70.0, ge=0.0, le=100.0, description="Fuzzy match score threshold (0-100)"
    )


class PriceLine(BaseModel):
    size: str
    price: float


class PriceAnswer(BaseModel):
    product_name: str
    product_code: Optional[str] = None
    category_name: Optional[str] = None
    subcategory_name: Optional[str] = None
    prices: List[PriceLine]


class ProductAnswer(BaseModel):
    product_name: str
    fields_used: List[str]
    details: List[str]  # bullet lines


class ChatResponse(BaseModel):
    answer: str
    matched_products: List[str]
    prices: List[PriceAnswer] = []
    product_details: List[ProductAnswer] = []
    price_list_meta: Dict[str, Any] = {}
    notes: List[str] = []
    clarifying_question: Optional[str] = None
    grounded_in: List[str] = Field(
        default_factory=lambda: ["paint_products.json", "pricelistnationalpaints.json"]
    )


# -----------------------------
# Core logic
# -----------------------------


def format_product_details(p: Dict[str, Any]) -> ProductAnswer:
    name = p.get("product_name", "Unknown product")
    fields = []
    bullets: List[str] = []

    # Choose common fields to expose
    for key in [
        "description",
        "uses",
        "advantages",
        "typical_properties",
        "packaging_size",
        "surface_preparation",
        "application_method",
        "recommended_system",
        "certificate_and_compliance",
        "application_instructions",
        "powder_properties",
        "coating_properties",
        "corrosion_testing",
        "mechanical_testing",
        "storage_conditions",
        "operating_temperature",
        "product_code",
    ]:
        val = p.get(key)
        if val is None:
            continue
        fields.append(key)
        if isinstance(val, str):
            bullets.extend(as_bullets(val))
        elif isinstance(val, list) or isinstance(val, dict):
            bullets.append(f"- {key.replace('_', ' ').title()}:")
            bullets.extend(as_bullets(val, indent=1))
        else:
            bullets.append(f"- {key.replace('_', ' ').title()}: {val}")

    return ProductAnswer(product_name=name, fields_used=fields, details=bullets)


def filter_prices_by_size_hints(
    entries: List[Dict[str, Any]], size_hints: List[str]
) -> List[Dict[str, Any]]:
    if not size_hints:
        return entries
    hints_norm = [normalize_name(h) for h in size_hints]
    filtered: List[Dict[str, Any]] = []
    for e in entries:
        prices = e.get("prices", [])
        match_any = False
        for pl in prices:
            size = normalize_name(str(pl.get("size", "")))
            if any(h in size for h in hints_norm):
                match_any = True
                break
        if match_any:
            filtered.append(e)
    # If filtering removed everything, fall back to original
    return filtered or entries


def compose_text_answer(
    matched_names: List[str],
    detail_answers: List[ProductAnswer],
    price_answers: List[PriceAnswer],
    meta: Dict[str, Any],
    notes: List[str],
    requested_price: bool,
) -> str:
    lines: List[str] = []
    if not matched_names:
        return "I could not confidently match any product from the uploaded files. Please specify the exact product name or code."

    if requested_price and price_answers:
        lines.append("Prices:")
        eff = meta.get("effective_date")
        cur = meta.get("currency", "")
        if eff or cur:
            lines.append(f"- Effective date: {eff or 'N/A'}; Currency: {cur or 'N/A'}")
        for pa in price_answers:
            header = f"- {pa.product_name}"
            extras = []
            if pa.product_code:
                extras.append(f"code {pa.product_code}")
            if pa.subcategory_name:
                extras.append(pa.subcategory_name)
            if pa.category_name:
                extras.append(pa.category_name)
            if extras:
                header += f" ({', '.join(extras)})"
            lines.append(header)
            for pl in pa.prices:
                lines.append(f"  - {pl.size}: {pl.price} {cur}")
        if notes:
            lines.append("Notes:")
            for n in notes:
                lines.append(f"- {n}")

    if detail_answers:
        if price_answers:
            lines.append("")  # spacing
        lines.append("Product details:")
        for d in detail_answers:
            lines.append(f"- {d.product_name}")
            for b in d.details:
                lines.append(f"  {b}")

    if not price_answers and not detail_answers:
        lines.append("I found these closest product matches. Please confirm which one you want:")
        for nm in matched_names:
            lines.append(f"- {nm}")

    return "\n".join(lines)


# -----------------------------
# FastAPI App
# -----------------------------

app = FastAPI(title="National Paints Chatbot (Local RAG)", version="1.0")


@app.get("/health")
def health():
    if not INDEX.products_list or not INDEX.prices_list:
        return {
            "status": "degraded",
            "reason": "Data not loaded",
            "need_files": [PRODUCTS_FILE.name, PRICES_FILE.name],
        }
    return {
        "status": "ok",
        "products_count": len(INDEX.products_list),
        "prices_count": len(INDEX.prices_list),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message is required.")

    # 1) Fuzzy match product names
    matches = INDEX.match_product_names(req.message, limit=max(req.top_k, 5))
    strong_matches = [(n, s) for (n, s) in matches if s >= req.confidence_threshold]
    matched_names = [n for (n, _s) in strong_matches]

    if not strong_matches:
        # If user included a code, try code-only price match
        code_candidates = re.findall(r"\b[A-Z]\d{2,4}[A-Z0-9]*\b", req.message.upper())
        price_answers: List[PriceAnswer] = []
        for code in code_candidates:
            code_entries = INDEX.get_price_by_code(code)
            for e in code_entries:
                pa = PriceAnswer(
                    product_name=e.get("product_name"),
                    product_code=e.get("product_code"),
                    category_name=e.get("category_name"),
                    subcategory_name=e.get("subcategory_name"),
                    prices=[
                        PriceLine(size=p["size"], price=float(p["price"]))
                        for p in e.get("prices", [])
                    ],
                )
                price_answers.append(pa)
        if price_answers:
            # Answer based on code even without name match
            text = compose_text_answer(
                matched_names=[f"code {c}" for c in code_candidates],
                detail_answers=[],
                price_answers=price_answers,
                meta=INDEX.price_meta,
                notes=(INDEX.price_meta.get("notes") or []),
                requested_price=True,
            )
            return ChatResponse(
                answer=text,
                matched_products=[f"code {c}" for c in code_candidates],
                prices=price_answers,
                product_details=[],
                price_list_meta=INDEX.price_meta,
                notes=(INDEX.price_meta.get("notes") or []),
                clarifying_question=None,
            )
        # No match; ask to clarify
        return ChatResponse(
            answer="I couldn't find a matching product. Please provide the exact product name or product code (e.g., A024).",
            matched_products=[],
            prices=[],
            product_details=[],
            price_list_meta=INDEX.price_meta,
            notes=(INDEX.price_meta.get("notes") or []),
            clarifying_question="Which exact product do you need?",
        )

    # 2) Determine intent
    wants_price = is_like_price_query(req.message)
    size_hints = extract_size_hints(req.message)

    # 3) Build answers
    product_detail_answers: List[ProductAnswer] = []
    price_answers: List[PriceAnswer] = []

    # Details from paint_products.json
    for nm in matched_names:
        prods = INDEX.get_products_by_name(nm)
        # Take first one per distinct name (there may be multiple variants under same name)
        if prods:
            product_detail_answers.append(format_product_details(prods[0]))

    # Prices from price list
    if wants_price:
        # Try fuzzy name match in price list as well
        # We will match against all price product names for broader coverage
        price_names = [r["product_name"] for r in INDEX.prices_list if r.get("product_name")]
        price_matches = process.extract(
            req.message, price_names, scorer=fuzz.WRatio, limit=10
        )
        # Keep above threshold
        price_names_sel = [name for (name, score, _idx) in price_matches if score >= req.confidence_threshold]
        # Also add exact name matches from matched_names
        price_names_sel.extend(matched_names)

        seen_norm = set()
        candidate_entries: List[Dict[str, Any]] = []
        for pn in price_names_sel:
            norm = normalize_name(pn)
            if norm in seen_norm:
                continue
            seen_norm.add(norm)
            candidate_entries.extend(INDEX.get_price_by_name(pn))

        # Filter by size hints if present
        candidate_entries = filter_prices_by_size_hints(candidate_entries, size_hints)

        # Deduplicate by (name, code, subcategory)
        seen_keys = set()
        for e in candidate_entries:
            key = (
                e.get("product_name"),
                e.get("product_code"),
                e.get("subcategory_name"),
            )
            if key in seen_keys:
                continue
            seen_keys.add(key)
            price_answers.append(
                PriceAnswer(
                    product_name=e.get("product_name"),
                    product_code=e.get("product_code"),
                    category_name=e.get("category_name"),
                    subcategory_name=e.get("subcategory_name"),
                    prices=[
                        PriceLine(size=p["size"], price=float(p["price"]))
                        for p in e.get("prices", [])
                    ],
                )
            )

    # 4) Compose textual answer, strictly from data
    answer_text = compose_text_answer(
        matched_names=matched_names,
        detail_answers=product_detail_answers,
        price_answers=price_answers,
        meta=INDEX.price_meta,
        notes=(INDEX.price_meta.get("notes") or []),
        requested_price=wants_price,
    )

    # 5) If the user clearly asked for price but none found, prompt to clarify size or provide a code
    clar_q = None
    if wants_price and not price_answers:
        clar_q = "I couldn't find a price for that product. Do you have a specific size (e.g., 18 Ltr Drum, 3.6 Ltr Gallon) or product code (e.g., A024)?"

    return ChatResponse(
        answer=answer_text,
        matched_products=matched_names,
        prices=price_answers,
        product_details=product_detail_answers,
        price_list_meta=INDEX.price_meta,
        notes=(INDEX.price_meta.get("notes") or []),
        clarifying_question=clar_q,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
