"""Hybrid retrieval: ChromaDB semantic search + BM25 keyword search."""

import hashlib
import os
import re
from pathlib import Path

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "postgresql_17_docs"
CORPUS_DIR = Path(os.getenv("CORPUS_DIR", "/app/corpus"))
EMBEDDING_MODEL_ID = os.getenv(
    "EMBEDDING_MODEL_ID",
    "sentence-transformers/all-MiniLM-L6-v2",
)

_encoder = None


def get_encoder():
    global _encoder
    if _encoder is None:
        _encoder = SentenceTransformer(EMBEDDING_MODEL_ID, device="cpu")
    return _encoder


def get_collection():
    client = chromadb.HttpClient(
        host=os.getenv("CHROMA_HOST", "chroma"),
        port=int(os.getenv("CHROMA_PORT", "8000")),
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def tokenize(text):
    return re.findall(r"[a-z0-9_]+", text.lower())


def split_document(text, max_chars=1400, overlap=200):
    """Split Markdown into chunks while retaining section headings."""
    sections = []
    current_heading = "Introduction"
    current_text = []

    for line in text.splitlines():
        if line.startswith("#"):
            if current_text:
                sections.append((current_heading, "\n".join(current_text)))
            current_heading = line.lstrip("#").strip()
            current_text = [line]
        else:
            current_text.append(line)

    if current_text:
        sections.append((current_heading, "\n".join(current_text)))

    chunks = []

    for heading, content in sections:
        content = content.strip()
        if not content:
            continue

        start = 0
        while start < len(content):
            end = min(start + max_chars, len(content))
            chunk = content[start:end].strip()

            if chunk:
                chunks.append((heading, chunk))

            if end == len(content):
                break

            start = end - overlap

    return chunks


def ingest_corpus(corpus_dir=None):
    """Read Markdown files and upsert their chunks into ChromaDB."""
    root = Path(corpus_dir) if corpus_dir else CORPUS_DIR

    if not root.exists():
        raise FileNotFoundError(f"Corpus directory not found: {root}")

    files = sorted(root.rglob("*.md"))
    if not files:
        raise ValueError(f"No Markdown documents found in {root}")

    records = []

    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        relative_path = str(file_path.relative_to(root))
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else file_path.stem

        for index, (section, chunk) in enumerate(split_document(text)):
            chunk_id = hashlib.sha256(
                f"{relative_path}:{index}".encode()
            ).hexdigest()

            records.append({
                "id": chunk_id,
                "document": chunk,
                "metadata": {
                    "source_id": relative_path,
                    "title": title,
                    "section": section,
                    "chunk_index": index,
                },
            })

    collection = get_collection()
    encoder = get_encoder()

    batch_size = 64
    for start in range(0, len(records), batch_size):
        batch = records[start:start + batch_size]
        documents = [item["document"] for item in batch]
        embeddings = encoder.encode(
            documents,
            normalize_embeddings=True,
        ).tolist()

        collection.upsert(
            ids=[item["id"] for item in batch],
            documents=documents,
            metadatas=[item["metadata"] for item in batch],
            embeddings=embeddings,
        )

    return {
        "documents": len(files),
        "chunks": len(records),
        "collection": COLLECTION_NAME,
    }


def hybrid_search(query, top_k=5):
    """Combine semantic and BM25 rankings using reciprocal rank fusion."""
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    collection = get_collection()
    total = collection.count()

    if total == 0:
        raise RuntimeError("Knowledge base is empty. Run ingest_corpus() first.")

    encoder = get_encoder()
    query_embedding = encoder.encode(
        [query],
        normalize_embeddings=True,
    ).tolist()

    vector_results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k * 3, total),
        include=["documents", "metadatas", "distances"],
    )

    all_records = collection.get(
        include=["documents", "metadatas"],
    )

    documents = all_records["documents"]
    metadatas = all_records["metadatas"]
    ids = all_records["ids"]

    tokenized_corpus = [tokenize(document) for document in documents]
    bm25 = BM25Okapi(tokenized_corpus)
    keyword_scores = bm25.get_scores(tokenize(query))

    keyword_order = sorted(
        range(len(keyword_scores)),
        key=lambda i: keyword_scores[i],
        reverse=True,
    )[:top_k * 3]

    fused = {}

    def add_rank(identifier, rank):
        fused[identifier] = fused.get(identifier, 0.0) + 1.0 / (60 + rank)

    vector_ids = vector_results["ids"][0]
    for rank, identifier in enumerate(vector_ids, start=1):
        add_rank(identifier, rank)

    for rank, index in enumerate(keyword_order, start=1):
        add_rank(ids[index], rank)

    id_to_index = {identifier: i for i, identifier in enumerate(ids)}

    ranked_ids = sorted(
        fused,
        key=lambda identifier: fused[identifier],
        reverse=True,
    )[:top_k]

    results = []

    for identifier in ranked_ids:
        index = id_to_index[identifier]
        metadata = metadatas[index]

        results.append({
            "chunk_id": identifier,
            "text": documents[index],
            "source_id": metadata["source_id"],
            "title": metadata["title"],
            "section": metadata["section"],
            "score": round(fused[identifier], 6),
            "citation": (
                f'{metadata["source_id"]}#{metadata["section"]}'
            ),
        })

    return results
