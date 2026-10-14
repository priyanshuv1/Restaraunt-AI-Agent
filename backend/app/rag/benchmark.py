"""Measure local embedding and Qdrant retrieval latency.

Run from backend/:
    python -m app.rag.benchmark --query "spicy vegetarian burger" --category Burgers --runs 10
"""
import argparse
from statistics import mean
from time import perf_counter

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.menu import MenuItem
from app.rag.embeddings import embed_texts, get_embedding_model
from app.rag.service import search_menu_by_embedding


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark DineMate menu RAG latency.")
    parser.add_argument("--query", default="spicy vegetarian burger")
    parser.add_argument("--category", default="Burgers")
    parser.add_argument("--runs", type=int, default=10)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    started = perf_counter()
    get_embedding_model()
    model_load_seconds = perf_counter() - started
    embed_texts([args.query])

    embedding_ms: list[float] = []
    retrieval_ms: list[float] = []
    total_ms: list[float] = []
    last_matches: list[dict] = []

    with SessionLocal() as db:
        menu_count = db.scalar(select(MenuItem.id).limit(1))
        for _ in range(args.runs):
            started = perf_counter()
            vector = embed_texts([args.query])[0].tolist()
            embedding_elapsed = (perf_counter() - started) * 1000
            embedding_ms.append(embedding_elapsed)

            started = perf_counter()
            last_matches = search_menu_by_embedding(
                db, vector, category=args.category, top_k=5
            )
            retrieval_elapsed = (perf_counter() - started) * 1000
            retrieval_ms.append(retrieval_elapsed)
            total_ms.append(embedding_elapsed + retrieval_elapsed)

    print("DineMate Qdrant RAG latency benchmark")
    print(f"Model load (first load, seconds): {model_load_seconds:.3f}")
    print(f"Menu has at least one item: {menu_count is not None}")
    print(f"Category filter: {args.category or '(none)'}")
    print(f"Runs: {args.runs}")
    print(f"Query embedding average (ms): {mean(embedding_ms):.2f}")
    print(f"Qdrant + SQL hydration average (ms): {mean(retrieval_ms):.2f}")
    print(f"End-to-end retrieval average (ms): {mean(total_ms):.2f}")
    print(f"End-to-end retrieval p95-ish (ms): {percentile(total_ms, 0.95):.2f}")
    print(f"Matches in final run: {len(last_matches)}")
    for match in last_matches:
        print(
            f"- {match['name']} [{match['category']}] "
            f"similarity={match['similarity']:.4f}"
        )


if __name__ == "__main__":
    main()
