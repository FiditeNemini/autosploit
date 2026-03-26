#!/usr/bin/env python3
"""
generate-embeddings.py — Generate embeddings for ExploitBot's CVE database.

Reads starter-cves.db, generates vector embeddings for each CVE description,
and stores them in the `embedding` column as float32 blobs.

Embedding strategies (in priority order):
  1. MLX model (local Apple Silicon) — best quality, ~768-dim
  2. sentence-transformers (if installed) — good quality, ~384-dim
  3. TF-IDF fallback — decent for keyword matching, 512-dim

Usage:
    python3 scripts/generate-embeddings.py
    python3 scripts/generate-embeddings.py --method tfidf          # force TF-IDF
    python3 scripts/generate-embeddings.py --method mlx            # force MLX
    python3 scripts/generate-embeddings.py --method sentence       # force sentence-transformers
    python3 scripts/generate-embeddings.py --batch-size 64         # adjust batch size
    python3 scripts/generate-embeddings.py --db path/to/cves.db    # custom DB path
"""

import argparse
import json
import math
import os
import re
import sqlite3
import struct
import sys
import time
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_DB = PROJECT_DIR / "ExploitBot" / "Resources" / "starter-cves.db"

# TF-IDF embedding dimension
TFIDF_DIM = 512

# Security/CVE-specific stopwords to remove
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "must", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out",
    "off", "over", "under", "again", "further", "then", "once",
    "and", "but", "or", "nor", "not", "no", "so", "too", "very",
    "that", "this", "these", "those", "it", "its", "which", "who",
    "whom", "what", "where", "when", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such",
    "than", "also", "only", "same", "just", "if", "any", "here",
    "there", "about", "up", "via", "allows", "allow", "could",
    "attacker", "attackers", "vulnerability", "vulnerable", "version",
    "versions", "prior", "aka", "certain", "product", "products",
}


# ---------------------------------------------------------------------------
# Method 1: MLX embeddings (Apple Silicon)
# ---------------------------------------------------------------------------

def try_mlx_embeddings():
    """Try to load MLX-based embedding model. Returns embedding function or None."""
    try:
        import mlx.core as mx
        import mlx.nn as nn
    except ImportError:
        return None

    # Try to find a suitable embedding model
    # Common locations for MLX models
    model_candidates = [
        os.path.expanduser("~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2"),
        os.path.expanduser("~/.cache/lm-studio/models/nomic-ai/nomic-embed-text-v1.5"),
    ]

    # For MLX, we'll use mlx-community models if available
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2", device="mps")

        def embed_batch(texts):
            embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
            return [emb.tolist() for emb in embeddings]

        print("  Using sentence-transformers with MPS (Apple GPU)")
        return embed_batch, model.get_sentence_embedding_dimension()
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Method 2: sentence-transformers
# ---------------------------------------------------------------------------

def try_sentence_transformers():
    """Try sentence-transformers library. Returns (embed_fn, dim) or None."""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")

        def embed_batch(texts):
            embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
            return [emb.tolist() for emb in embeddings]

        dim = model.get_sentence_embedding_dimension()
        print(f"  Using sentence-transformers (all-MiniLM-L6-v2, {dim}-dim)")
        return embed_batch, dim
    except ImportError:
        return None
    except Exception as e:
        print(f"  [!] sentence-transformers error: {e}")
        return None


# ---------------------------------------------------------------------------
# Method 3: TF-IDF embeddings (always available, no dependencies)
# ---------------------------------------------------------------------------

class TFIDFEmbedder:
    """Simple TF-IDF embedder using hashing trick for fixed-dimension vectors.
    No external dependencies needed."""

    def __init__(self, dim=TFIDF_DIM):
        self.dim = dim
        self.idf = None
        self.vocab = None

    def _tokenize(self, text: str) -> list:
        """Tokenize and clean text."""
        text = text.lower()
        # Keep alphanumeric, hyphens (for CVE IDs), dots (for versions)
        tokens = re.findall(r'[a-z0-9][\w\-\.]*[a-z0-9]|[a-z0-9]', text)
        # Remove stopwords
        tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
        # Add bigrams for common security phrases
        bigrams = []
        for i in range(len(tokens) - 1):
            bigrams.append(f"{tokens[i]}_{tokens[i+1]}")
        return tokens + bigrams

    def _hash_token(self, token: str) -> int:
        """Hash a token to a bucket index using FNV-1a."""
        h = 2166136261
        for byte in token.encode("utf-8"):
            h ^= byte
            h = (h * 16777619) & 0xFFFFFFFF
        return h % self.dim

    def fit(self, documents: list):
        """Compute IDF weights from corpus."""
        n_docs = len(documents)
        doc_freq = Counter()

        for doc in documents:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                bucket = self._hash_token(token)
                doc_freq[bucket] += 1

        # IDF = log(N / (1 + df))
        self.idf = {}
        for bucket, df in doc_freq.items():
            self.idf[bucket] = math.log(n_docs / (1 + df))

    def embed(self, text: str) -> list:
        """Generate a TF-IDF embedding vector for a text."""
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0] * self.dim

        # Term frequency
        tf = Counter()
        for token in tokens:
            bucket = self._hash_token(token)
            tf[bucket] += 1

        # Normalize TF
        max_tf = max(tf.values()) if tf else 1

        # TF-IDF vector
        vector = [0.0] * self.dim
        for bucket, count in tf.items():
            normalized_tf = 0.5 + 0.5 * (count / max_tf)  # augmented TF
            idf = self.idf.get(bucket, 1.0) if self.idf else 1.0
            vector[bucket] += normalized_tf * idf

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    def embed_batch(self, texts: list) -> list:
        """Generate embeddings for a batch of texts."""
        return [self.embed(text) for text in texts]


def build_tfidf_embedder(descriptions: list):
    """Build and fit a TF-IDF embedder on the corpus."""
    embedder = TFIDFEmbedder(dim=TFIDF_DIM)
    print(f"  Fitting TF-IDF on {len(descriptions):,} documents ({TFIDF_DIM}-dim)...")
    embedder.fit(descriptions)

    def embed_batch(texts):
        return embedder.embed_batch(texts)

    return embed_batch, TFIDF_DIM


# ---------------------------------------------------------------------------
# Embedding storage
# ---------------------------------------------------------------------------

def floats_to_blob(floats: list) -> bytes:
    """Convert a list of floats to a binary blob (float32 array).
    This matches CVEService.swift which reads float32 from blob."""
    return struct.pack(f"{len(floats)}f", *floats)


def blob_to_floats(blob: bytes) -> list:
    """Convert a binary blob back to list of floats."""
    count = len(blob) // 4
    return list(struct.unpack(f"{count}f", blob))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for CVE database")
    parser.add_argument("--db", type=str, default=str(DEFAULT_DB), help="Path to CVE database")
    parser.add_argument("--method", choices=["auto", "mlx", "sentence", "tfidf"],
                        default="auto", help="Embedding method (default: auto-detect best)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for embedding generation")
    parser.add_argument("--force", action="store_true", help="Regenerate all embeddings (overwrite existing)")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("Run build-cve-db.py first to create the database.")
        sys.exit(1)

    print("ExploitBot CVE Embedding Generator")
    print("=" * 70)
    print(f"  Database:     {db_path}")
    print(f"  Method:       {args.method}")
    print(f"  Batch size:   {args.batch_size}")

    # Connect to DB
    conn = sqlite3.connect(str(db_path))

    # Count CVEs needing embeddings
    if args.force:
        total = conn.execute("SELECT COUNT(*) FROM cves").fetchone()[0]
        print(f"  CVEs to embed: {total:,} (--force: all)")
    else:
        total = conn.execute("SELECT COUNT(*) FROM cves WHERE embedding IS NULL").fetchone()[0]
        already = conn.execute("SELECT COUNT(*) FROM cves WHERE embedding IS NOT NULL").fetchone()[0]
        print(f"  CVEs to embed: {total:,} (already done: {already:,})")

    if total == 0:
        print("\n  Nothing to do. All CVEs already have embeddings.")
        print("  Use --force to regenerate all embeddings.")
        conn.close()
        return

    # Select embedding method
    embed_fn = None
    embed_dim = None

    if args.method in ("auto", "mlx"):
        result = try_mlx_embeddings()
        if result:
            embed_fn, embed_dim = result

    if embed_fn is None and args.method in ("auto", "sentence"):
        result = try_sentence_transformers()
        if result:
            embed_fn, embed_dim = result

    if embed_fn is None:
        if args.method in ("auto", "tfidf"):
            # Load all descriptions for TF-IDF fitting
            print("\n  Loading descriptions for TF-IDF fitting...")
            cursor = conn.execute("SELECT description FROM cves WHERE description IS NOT NULL")
            all_descs = [row[0] for row in cursor.fetchall()]
            embed_fn, embed_dim = build_tfidf_embedder(all_descs)
            del all_descs  # free memory
        else:
            print(f"\n  Error: Requested method '{args.method}' not available.")
            print("  Install requirements:")
            print("    MLX: pip3 install mlx sentence-transformers")
            print("    sentence-transformers: pip3 install sentence-transformers")
            conn.close()
            sys.exit(1)

    print(f"  Embedding dimension: {embed_dim}")

    # Process in batches
    print(f"\n  Generating embeddings...")
    start_time = time.time()

    if args.force:
        query = "SELECT id, description, severity, cpeVendor, cpeProduct, cpeVersionStart, cpeVersionEnd, tags FROM cves ORDER BY id"
    else:
        query = "SELECT id, description, severity, cpeVendor, cpeProduct, cpeVersionStart, cpeVersionEnd, tags FROM cves WHERE embedding IS NULL ORDER BY id"

    cursor = conn.execute(query)
    processed = 0
    batch_ids = []
    batch_texts = []

    while True:
        rows = cursor.fetchmany(args.batch_size)
        if not rows:
            break

        batch_ids = [row[0] for row in rows]
        # Build composite embedding text:
        # "{cve_id} | {severity} | {vendor} {product} {version_range} | {tags} | {description}"
        batch_texts = []
        for row in rows:
            cve_id = row[0] or ""
            desc = row[1] or ""
            severity = row[2] or ""
            vendor = row[3] or ""
            product = row[4] or ""
            ver_start = row[5] or ""
            ver_end = row[6] or ""
            tags = row[7] or ""

            version_range = ""
            if ver_start and ver_end:
                version_range = f"{ver_start} through {ver_end}"
            elif ver_start:
                version_range = ver_start
            elif ver_end:
                version_range = f"up to {ver_end}"

            # Replace tag abbreviations with searchable phrases
            tag_phrases = tags.replace(",", " ") if tags else ""

            composite = f"{cve_id} | {severity} | {vendor} {product} {version_range} | {tag_phrases} | {desc}"
            batch_texts.append(composite.strip())

        # Generate embeddings
        try:
            embeddings = embed_fn(batch_texts)
        except Exception as e:
            print(f"\n  [!] Error embedding batch at {processed}: {e}")
            # Try one at a time
            embeddings = []
            for text in batch_texts:
                try:
                    emb = embed_fn([text])[0]
                    embeddings.append(emb)
                except Exception:
                    embeddings.append([0.0] * embed_dim)

        # Store embeddings as float32 blobs
        for cve_id, embedding in zip(batch_ids, embeddings):
            blob = floats_to_blob(embedding)
            conn.execute("UPDATE cves SET embedding = ? WHERE id = ?", (blob, cve_id))

        conn.commit()
        processed += len(rows)

        # Progress
        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        eta = (total - processed) / rate if rate > 0 else 0
        print(f"  {processed:,}/{total:,} ({processed*100//total}%) "
              f"  {rate:.0f} CVEs/sec  ETA: {int(eta)}s", end="\r", flush=True)

    elapsed = time.time() - start_time
    print(f"\n\n  Done: {processed:,} embeddings generated in {elapsed:.1f}s")

    # Verify
    with_embeddings = conn.execute("SELECT COUNT(*) FROM cves WHERE embedding IS NOT NULL").fetchone()[0]
    total_cves = conn.execute("SELECT COUNT(*) FROM cves").fetchone()[0]
    print(f"  Coverage: {with_embeddings:,}/{total_cves:,} CVEs have embeddings "
          f"({with_embeddings*100//total_cves}%)")

    # Sample check — verify a random embedding is correct dimension
    sample = conn.execute("SELECT embedding FROM cves WHERE embedding IS NOT NULL LIMIT 1").fetchone()
    if sample and sample[0]:
        sample_floats = blob_to_floats(sample[0])
        print(f"  Embedding dimension: {len(sample_floats)} (expected: {embed_dim})")
        print(f"  Sample vector norm: {math.sqrt(sum(v*v for v in sample_floats)):.4f} (should be ~1.0)")

    # Optimize
    print("  Optimizing database...")
    conn.execute("VACUUM")
    conn.commit()

    db_size = db_path.stat().st_size
    print(f"  Final database size: {db_size / (1024*1024):.1f} MB")

    conn.close()
    print(f"\n  Embeddings written to: {db_path}")


if __name__ == "__main__":
    main()
