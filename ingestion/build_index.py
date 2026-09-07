"""Build the optional multilingual Qdrant index from committed documents."""

from __future__ import annotations

import argparse

from app.data import load_documents

from .chunking import structure_chunks
from .corpus import build_corpus
from .indexing import build_qdrant_hybrid_index, build_qdrant_index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--collection", default="napas_documents")
    parser.add_argument("--hybrid", action="store_true", help="build parallel dense and sparse collections")
    args = parser.parse_args()
    build_corpus(args.data_dir)
    documents = load_documents(f"{args.data_dir}/docs")
    chunks = [chunk for document in documents for chunk in structure_chunks(document)]
    indexed = (build_qdrant_hybrid_index(chunks, args.qdrant_url, args.collection)
               if args.hybrid else build_qdrant_index(chunks, args.qdrant_url, args.collection))
    print({"indexed": indexed, "collection": args.collection, "hybrid": args.hybrid})


if __name__ == "__main__":
    main()
