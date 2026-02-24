from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None


def ingest_pdf(path: str, chunk_size: int = 1200, overlap: int = 120) -> dict:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    pdf_path = Path(path).resolve()
    if not pdf_path.exists() or PdfReader is None:
        return {"chunks": [], "page_count": 0, "query": lambda _: []}
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return {"chunks": [], "page_count": 0, "query": lambda _: []}

    text_parts = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            text_parts.append("")
    text = "\n".join(text_parts).strip()

    chunks = []
    stride = chunk_size - overlap
    i = 0
    idx = 0
    while i < len(text):
        chunks.append({"id": idx, "text": text[i : i + chunk_size]})
        idx += 1
        i += stride

    def query(question: str, top_k: int = 3):
        tokens = [t for t in re.findall(r"[A-Za-z0-9_]+", question.lower()) if len(t) > 2]
        scored = []
        for chunk in chunks:
            lowered = chunk["text"].lower()
            score = sum(lowered.count(tok) for tok in tokens)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    return {"chunks": chunks, "page_count": len(reader.pages), "query": query}


def query_dialectical_synthesis(ingested_pdf: dict) -> list[dict]:
    query_fn: Callable[[str], list[dict]] = ingested_pdf.get("query", lambda _: [])
    return query_fn("What does the report say about Dialectical Synthesis?")


KEYWORDS = [
    "Dialectical Synthesis",
    "Fan-In / Fan-Out",
    "Metacognition",
    "State Synchronization",
]


def extract_keyword_contexts(ingested_pdf: dict, keywords: list[str] | None = None) -> dict[str, list[str]]:
    keywords = keywords or KEYWORDS
    chunks = ingested_pdf.get("chunks", [])
    contexts: dict[str, list[str]] = {keyword: [] for keyword in keywords}
    for chunk in chunks:
        text = chunk["text"]
        lowered = text.lower()
        for keyword in keywords:
            if keyword.lower() in lowered:
                contexts[keyword].append(text[:320])
    return contexts


def extract_paths_from_text(text: str) -> list[str]:
    pattern = re.compile(
        r"([A-Za-z0-9_\-./\\]+\.(?:py|md|json|ya?ml|toml|txt|tsx?|jsx?|png|jpg|jpeg|svg))"
    )
    return sorted(set(match.group(1).replace("\\", "/") for match in pattern.finditer(text)))


def verify_paths(paths: list[str], repo_path: str) -> dict[str, list[str]]:
    root = Path(repo_path).resolve()
    verified: list[str] = []
    hallucinated: list[str] = []
    for rel in paths:
        if (root / rel).exists():
            verified.append(rel)
        else:
            hallucinated.append(rel)
    return {"verified": verified, "hallucinated": hallucinated}


def extract_images_from_pdf(path: str, output_dir: str | None = None) -> list[str]:
    pdf_path = Path(path).resolve()
    if not pdf_path.exists() or PdfReader is None:
        return []
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return []

    out_base = Path(output_dir).resolve() if output_dir else (pdf_path.parent / f"{pdf_path.stem}_images")
    out_base.mkdir(parents=True, exist_ok=True)
    image_paths: list[str] = []
    for page_idx, page in enumerate(reader.pages):
        images = getattr(page, "images", [])
        for image_idx, img in enumerate(images):
            data = getattr(img, "data", None)
            if not data:
                continue
            ext = Path(getattr(img, "name", f"p{page_idx}_img{image_idx}.bin")).suffix or ".bin"
            out = out_base / f"page_{page_idx + 1}_img_{image_idx + 1}{ext}"
            out.write_bytes(data)
            image_paths.append(str(out))
    return image_paths
