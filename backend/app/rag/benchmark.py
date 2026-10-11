"""Measure local model load, query embedding, database search and total latency.

Run from backend/:
    python -m app.rag.benchmark --query "spicy vegetarian burger" --category Burgers --runs 10
"""
import argparse
from statistics import mean
from time import perf_counter

from sqlalchemy import select, func

from app.db.session import SessionLocal
from app.models.menu_embedding import MenuEmbedding
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

    # Warm up once so model initialization isn't mixed into steady-state latency.
    embed_texts([args.query])

    embedding_ms: list[float] = []
    db_ms: list[float] = []
    total_ms: list[float] = []
    last_matches: list[dict] = []

    with SessionLocal() as db:
        indexed_count = db.scalar(select(func.count()).select_from(MenuEmbedding)) or 0
        for _ in range(args.runs):
            started = perf_counter()
            vector = embed_texts([args.query])[0].tolist()
            embedding_ms.append((perf_counter() - started) * 1000)

            started = perf_counter()
            last_matches = search_menu_by_embedding(
                db, vector, category=args.category, top_k=5
            )
            db_ms.append((perf_counter() - started) * 1000)
            total_ms.append(embedding_ms[-1] + db_ms[-1])

    print("DineMate RAG latency benchmark")
    print(f"Model load (first load, seconds): {model_load_seconds:.3f}")
    print(f"Indexed menu items: {indexed_count}")
    print(f"Category filter: {args.category or '(none)'}")
    print(f"Runs: {args.runs}")
    print(f"Query embedding average (ms): {mean(embedding_ms):.2f}")
    print(f"Database retrieval average (ms): {mean(db_ms):.2f}")
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
