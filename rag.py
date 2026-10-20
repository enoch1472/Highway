"""
rag.py - Retrieval-Augmented Generation for The UK Highway Code.

This module powers intelligent rule discovery for The Zebra Crossing Assistant.
It combines dense vector semantic search (SentenceTransformers + ChromaDB) with
sparse keyword matching (BM25) using Reciprocal Rank Fusion (RRF).

Why Hybrid Search?
- Dense embeddings understand conceptual intent (e.g. "someone on the side of the road waiting").
- BM25 ensures precision for specific technical terms, crossing names (Zebra, Pelican,
  Puffin, Toucan, Pegasus), and exact Highway Code rule numbers.

Domain Guardrail:
- If the best cosine distance exceeds 0.52, the assistant recognizes the query as
  outside official road safety scope and safely refuses to hallucinate advice.
"""

import os
import sys
import re
import math
import hashlib
from typing import List, Dict, Tuple, Optional

# Ensure UTF-8 stdout for Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import chromadb
from sentence_transformers import SentenceTransformer


class SimpleBM25:
    """
    Lightweight, dependency-free BM25 (Best Matching 25) implementation.
    Ranks documents based on keyword frequency and inverse document frequency.
    """
    def __init__(self, corpus: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        self.doc_lens = [len(doc) for doc in self.tokenized_corpus]
        self.avg_doc_len = sum(self.doc_lens) / max(self.corpus_size, 1)

        # Precompute document frequencies for each term
        self.doc_freqs: Dict[str, int] = {}
        for doc in self.tokenized_corpus:
            for term in set(doc):
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        # Robertson-Sparck Jones IDF with add-0.5 smoothing
        self.idf: Dict[str, float] = {}
        for term, freq in self.doc_freqs.items():
            self.idf[term] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def _tokenize(self, text: str) -> List[str]:
        """Extracts lowercase alphanumeric words."""
        return [w.lower() for w in re.findall(r"\b[A-Za-z0-9_-]+\b", text)]

    def score(self, query: str) -> List[float]:
        """Calculates BM25 relevance score for each document in the corpus."""
        q_tokens = self._tokenize(query)
        scores = [0.0] * self.corpus_size

        for term in q_tokens:
            if term not in self.idf:
                continue
            idf_val = self.idf[term]
            for doc_idx, doc_tokens in enumerate(self.tokenized_corpus):
                term_count = doc_tokens.count(term)
                if term_count == 0:
                    continue
                doc_len = self.doc_lens[doc_idx]
                numerator = term_count * (self.k1 + 1.0)
                denominator = term_count + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                scores[doc_idx] += idf_val * (numerator / denominator)

        return scores


class RuleRAG:
    """
    Road safety knowledge retriever backed by ChromaDB and BM25.
    Preserves Highway Code legal authority and enforces calibrated confidence guardrails.
    """
    DEFAULT_DISTANCE_THRESHOLD = 0.52

    def __init__(
        self,
        data_path: str = "data/rules.txt",
        persist_dir: str = "./chroma_db",
        force_reindex: bool = False
    ):
        self.data_path = data_path
        self.persist_dir = persist_dir

        print("[RAG] Loading embedding model 'all-MiniLM-L6-v2'...", flush=True)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self.client = chromadb.PersistentClient(path=self.persist_dir)

        self._check_and_init_collection(force_reindex=force_reindex)
        self._init_bm25()

    def _compute_rules_hash(self) -> str:
        """Calculates SHA-256 fingerprint of the rules file to auto-detect updates."""
        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Rules database file not found at: {self.data_path}")
        with open(self.data_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _get_stored_hash_path(self) -> str:
        return os.path.join(self.persist_dir, ".rules_hash")

    def _check_and_init_collection(self, force_reindex: bool = False):
        """Initializes ChromaDB collection, re-indexing automatically when rules change."""
        current_hash = self._compute_rules_hash()
        stored_hash_file = self._get_stored_hash_path()
        stored_hash = None

        if os.path.exists(stored_hash_file):
            try:
                with open(stored_hash_file, "r", encoding="utf-8") as f:
                    stored_hash = f.read().strip()
            except Exception:
                stored_hash = None

        need_reindex = force_reindex or (stored_hash != current_hash)

        if need_reindex:
            print("[RAG] Rule changes detected. Re-indexing ChromaDB collection...", flush=True)
            try:
                self.client.delete_collection("traffic_rules")
            except Exception:
                pass

        self.collection = self.client.get_or_create_collection(
            name="traffic_rules",
            metadata={"hnsw:space": "cosine"}
        )

        if self.collection.count() == 0 or need_reindex:
            self._ingest_rules()
            os.makedirs(self.persist_dir, exist_ok=True)
            with open(stored_hash_file, "w", encoding="utf-8") as f:
                f.write(current_hash)
        else:
            print(f"[RAG] Loaded existing knowledge base with {self.collection.count()} rules.", flush=True)

    def _ingest_rules(self):
        """Parses rules.txt into structured rule chunks and encodes into ChromaDB."""
        with open(self.data_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        # Split on rule headers e.g. [RULE 195]
        raw_chunks = [c.strip() for c in re.split(r"(?=\[RULE\s+[^\]]+\])", content) if c.strip()]
        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(raw_chunks):
            if not chunk.startswith("[RULE"):
                continue

            lines = chunk.splitlines()
            first_line = lines[0].strip()

            rule_id_match = re.search(r"\[(RULE\s+[^\]]+)\]", first_line)
            rule_id = rule_id_match.group(1).strip() if rule_id_match else f"RULE_{i+1}"

            # Preserve legal authority: MUST (mandatory law) vs SHOULD (advisory)
            legal_weight = "MUST" if ("[MUST]" in first_line or "MUST" in chunk) else "SHOULD"

            clean_header = first_line
            title_match = re.sub(r"\[RULE\s+[^\]]+\]\s*\[(MUST|SHOULD)\]\s*", "", first_line)
            title = title_match.strip() if title_match else first_line

            documents.append(chunk)
            metadatas.append({
                "rule_id": rule_id,
                "header": clean_header,
                "title": title,
                "legal_weight": legal_weight,
                "text": chunk
            })
            ids.append(f"doc_{i}_{re.sub(r'[^A-Za-z0-9_]', '_', rule_id)}")

        print(f"[RAG] Encoding {len(documents)} Highway Code rules with MiniLM...", flush=True)
        embeddings = self.embedder.encode(documents, show_progress_bar=False).tolist()

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        print(f"[RAG] Successfully indexed {len(documents)} official Highway Code rules.", flush=True)

    def _init_bm25(self):
        """Prepares BM25 index over all indexed rule documents."""
        all_data = self.collection.get(include=["documents", "metadatas"])
        self.all_docs = all_data["documents"]
        self.all_metas = all_data["metadatas"]
        self.bm25 = SimpleBM25(self.all_docs)

    @staticmethod
    def _format_rule_match(doc: str, meta: Dict, distance: float) -> Dict:
        """Helper to create standardized rule payload."""
        return {
            "rule_id": meta.get("rule_id", "Unknown"),
            "header": meta.get("header", ""),
            "title": meta.get("title", meta.get("header", "")),
            "legal_weight": meta.get("legal_weight", "SHOULD"),
            "text": doc,
            "distance": round(distance, 4)
        }

    @staticmethod
    def _accumulate_rrf(rrf_scores: Dict[str, float], rid: str, rank: int, k: float = 60.0):
        """Adds Reciprocal Rank Fusion score for a given rank."""
        rrf_scores[rid] = rrf_scores.get(rid, 0.0) + 1.0 / (k + rank)

    def retrieve(
        self,
        query: str,
        raw_question: Optional[str] = None,
        top_k: int = 3,
        distance_threshold: Optional[float] = None,
        use_hybrid: bool = True
    ) -> Tuple[Optional[List[Dict]], str]:
        """
        Retrieves relevant rules using dense semantic search + BM25 keyword matching.
        Enforces distance guardrail to reject out-of-domain queries safely.
        """
        if distance_threshold is None:
            distance_threshold = self.DEFAULT_DISTANCE_THRESHOLD

        search_query = (raw_question or query).strip()
        if not search_query:
            return None, "Empty query provided."

        # Dense similarity search
        query_embedding = self.embedder.encode([search_query]).tolist()
        dense_results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(max(top_k * 3, 5), self.collection.count()),
            include=["documents", "metadatas", "distances"]
        )

        dense_docs = dense_results["documents"][0]
        dense_metas = dense_results["metadatas"][0]
        dense_dists = dense_results["distances"][0]

        if not dense_docs:
            return None, "No matching rules found in database."

        # Guardrail check: refuse out-of-domain queries
        best_distance = dense_dists[0]
        if best_distance > distance_threshold:
            return None, (
                f"Domain guardrail triggered: closest rule distance {best_distance:.3f} "
                f"exceeds safety threshold {distance_threshold}."
            )

        if not use_hybrid:
            retrieved = [
                self._format_rule_match(doc, meta, dist)
                for doc, meta, dist in zip(dense_docs[:top_k], dense_metas[:top_k], dense_dists[:top_k])
            ]
            return retrieved, "Success"

        # Hybrid Ranking via Reciprocal Rank Fusion (RRF)
        bm25_scores = self.bm25.score(search_query)
        bm25_ranked_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)

        rrf_scores: Dict[str, float] = {}
        doc_store: Dict[str, Tuple[str, Dict, float]] = {}

        # Accumulate Dense RRF scores
        for rank, (doc, meta, dist) in enumerate(zip(dense_docs, dense_metas, dense_dists)):
            rid = meta.get("rule_id", f"idx_{rank}")
            self._accumulate_rrf(rrf_scores, rid, rank)
            doc_store[rid] = (doc, meta, dist)

        # Accumulate Sparse BM25 RRF scores
        for rank, doc_idx in enumerate(bm25_ranked_indices[:min(10, len(bm25_ranked_indices))]):
            if bm25_scores[doc_idx] <= 0.0:
                continue
            meta = self.all_metas[doc_idx]
            doc = self.all_docs[doc_idx]
            rid = meta.get("rule_id", f"idx_{doc_idx}")
            self._accumulate_rrf(rrf_scores, rid, rank)
            if rid not in doc_store:
                doc_store[rid] = (doc, meta, 0.5)

        # Select top-k rules by combined RRF score
        sorted_rids = sorted(rrf_scores.keys(), key=lambda r: rrf_scores[r], reverse=True)[:top_k]
        retrieved_items = [
            self._format_rule_match(*doc_store[rid])
            for rid in sorted_rids
        ]

        return retrieved_items, "Success"

    def search_by_keyword(self, keyword: str, max_results: int = 8) -> List[Dict]:
        """Convenience method for searching rules directly by keyword or rule number."""
        kw = keyword.strip().lower()
        matched = []
        for doc, meta in zip(self.all_docs, self.all_metas):
            rule_id = meta.get("rule_id", "").lower()
            header = meta.get("header", "").lower()
            text = doc.lower()
            if kw in rule_id or kw in header or kw in text:
                matched.append(self._format_rule_match(doc, meta, 0.0))
                if len(matched) >= max_results:
                    break
        return matched

    def get_all_rules_summary(self) -> List[Dict]:
        """Returns clean catalog of all loaded rules for interactive browsing."""
        summary = []
        for i, meta in enumerate(self.all_metas):
            summary.append({
                "index": i + 1,
                "rule_id": meta.get("rule_id", ""),
                "header": meta.get("header", ""),
                "title": meta.get("title", ""),
                "legal_weight": meta.get("legal_weight", "SHOULD"),
                "text": meta.get("text", "")
            })
        return summary
