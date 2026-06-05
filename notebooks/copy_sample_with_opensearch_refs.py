#!/usr/bin/env python3
"""
Copy the first N **test** cases (DICOMs under data/test only — not index/train pool)
plus metadata, then fetch K similar references per case from OpenSearch.

Cases are taken only from paths under ``<dicom-root>/<cases-subdir>`` (default:
``data/test``). Use ``data/test_metadata.json`` by default (image_path like
``test/PATIENT_....dcm``).

Run from repo root (recommended):
  python notebooks/copy_sample_with_opensearch_refs.py --out-dir data/sample_50_opensearch

Requires: OpenSearch reachable (same env vars as backend), PyTorch + open_clip,
pydicom, opensearch-py. DICOM files must exist under --dicom-root (default: data/).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv_files() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for p in (REPO_ROOT / "backend" / ".env", REPO_ROOT / ".env"):
        if p.is_file():
            load_dotenv(p)


def _ensure_backend_path() -> None:
    backend = REPO_ROOT / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))


def _connect_opensearch():
    from opensearchpy import OpenSearch, RequestsHttpConnection

    host = os.environ.get("OPENSEARCH_HOST", "localhost")
    port = int(os.environ.get("OPENSEARCH_PORT", "9200"))
    user = os.environ.get("OPENSEARCH_USER")
    password = os.environ.get("OPENSEARCH_PASSWORD")
    use_ssl = os.environ.get("OPENSEARCH_USE_SSL", "").lower() in ("1", "true", "yes")
    verify = os.environ.get("OPENSEARCH_VERIFY_CERTS", "").lower() in ("1", "true", "yes")

    http_auth = None
    if user and password:
        http_auth = (user, password)

    client = OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=http_auth,
        use_ssl=use_ssl,
        verify_certs=verify,
        connection_class=RequestsHttpConnection,
        timeout=60,
    )
    if not client.ping():
        raise RuntimeError(f"OpenSearch ping failed at {host}:{port}")
    return client


def search_similar_by_embedding(
    client,
    index_name: str,
    embedding: List[float],
    k: int,
    exclude_image_paths: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """k-NN search; drop hits whose image_path is in exclude_image_paths (e.g. self)."""
    exclude_image_paths = exclude_image_paths or set()
    retrieve = max(k * 4, k + 5)

    body = {
        "size": retrieve,
        "query": {
            "knn": {
                "embedding": {
                    "vector": embedding,
                    "k": retrieve,
                }
            }
        },
        "_source": {
            "includes": ["image_path", "short_description", "full_description"],
        },
    }
    response = client.search(index=index_name, body=body)
    out: List[Dict[str, Any]] = []
    for hit in response["hits"]["hits"]:
        src = hit["_source"]
        ip = src.get("image_path", "")
        if ip in exclude_image_paths:
            continue
        out.append(
            {
                "image_path": ip,
                "short_description": src.get("short_description", ""),
                "full_description": src.get("full_description", ""),
                "score": float(hit["_score"]),
                "_id": hit["_id"],
            }
        )
        if len(out) >= k:
            break
    return out


def resolve_path(base: Path, rel_or_abs: str) -> Path:
    if os.path.isabs(rel_or_abs):
        return Path(rel_or_abs)
    return base / rel_or_abs


def copy_dicom_safe(src: Path, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not src.is_file():
        logger.warning("Missing source DICOM: %s", src)
        return False
    shutil.copy2(src, dest)
    return True


def is_under_subdir(dicom_root: Path, image_path: str, subdir: str) -> bool:
    """True if the resolved file path lies under dicom_root / subdir."""
    if not subdir:
        return True
    try:
        if os.path.isabs(image_path):
            p = Path(image_path).resolve()
        else:
            p = (dicom_root / image_path).resolve()
        root = (dicom_root / subdir).resolve()
        p.relative_to(root)
        return True
    except ValueError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy first N metadata cases + OpenSearch similar references."
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=REPO_ROOT / "data" / "test_metadata.json",
        help="Path to metadata JSON (default: data/test_metadata.json).",
    )
    parser.add_argument(
        "--dicom-root",
        type=Path,
        default=REPO_ROOT / "data",
        help="Base directory for relative image_path entries (same as backend dicom_data_path).",
    )
    parser.add_argument(
        "--cases-subdir",
        default="test",
        help=(
            "Only include rows whose DICOM resolves under <dicom-root>/<cases-subdir> "
            '(default: "test", i.e. data/test). Set to empty string to disable (not recommended).'
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Output directory (created if missing).",
    )
    parser.add_argument(
        "--n-cases",
        type=int,
        default=50,
        help="Number of cases to take from the start of the test-only list.",
    )
    parser.add_argument(
        "--k-similar",
        type=int,
        default=5,
        help="Similar references per case from OpenSearch.",
    )
    parser.add_argument(
        "--index-name",
        default=os.environ.get("INDEX_NAME", "rtg_scans_index"),
        help="OpenSearch index name (default: rtg_scans_index or INDEX_NAME env).",
    )
    parser.add_argument(
        "--clip-model",
        default=os.environ.get(
            "CLIP_MODEL_NAME",
            "hf-hub:luhuitong/CLIP-ViT-L-14-448px-MedICaT-ROCO",
        ),
        help="CLIP model id (must match index embeddings).",
    )
    parser.add_argument(
        "--skip-opensearch",
        action="store_true",
        help="Only copy cases + metadata; skip embedding and OpenSearch.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    metadata_path = args.metadata
    if not metadata_path.is_absolute():
        metadata_path = REPO_ROOT / metadata_path
    dicom_root = args.dicom_root
    if not dicom_root.is_absolute():
        dicom_root = REPO_ROOT / dicom_root

    with open(metadata_path, encoding="utf-8") as f:
        all_meta: List[Dict[str, Any]] = json.load(f)
    if not isinstance(all_meta, list):
        raise SystemExit("metadata file must be a JSON array")

    cases_subdir = (args.cases_subdir or "").strip().replace("\\", "/")
    eligible: List[Dict[str, Any]] = []
    for item in all_meta:
        ip = item.get("image_path", "")
        if not ip:
            continue
        if cases_subdir and not is_under_subdir(dicom_root, ip, cases_subdir):
            continue
        eligible.append(item)

    if not eligible:
        under = (dicom_root / cases_subdir) if cases_subdir else dicom_root
        raise SystemExit(
            f"No metadata rows under {under}. Check --metadata, --dicom-root, and --cases-subdir."
        )

    subset = eligible[: args.n_cases]
    logger.info(
        "Using %d case(s) from %d eligible (under %s); source had %d rows.",
        len(subset),
        len(eligible),
        dicom_root / cases_subdir if cases_subdir else dicom_root,
        len(all_meta),
    )
    out_dir = args.out_dir
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    cases_dir = out_dir / "cases"
    ref_dir = out_dir / "references"
    cases_dir.mkdir(parents=True, exist_ok=True)
    ref_dir.mkdir(parents=True, exist_ok=True)

    copied_cases = 0
    for i, item in enumerate(subset):
        ip = item.get("image_path", "")
        if not ip:
            logger.warning("Item %s: no image_path, skipping", i)
            continue
        src = resolve_path(dicom_root, ip)
        dest = cases_dir / Path(ip).name
        if copy_dicom_safe(src, dest):
            copied_cases += 1

    cases_json_path = out_dir / "cases_metadata.json"
    with open(cases_json_path, "w", encoding="utf-8") as f:
        json.dump(subset, f, ensure_ascii=False, indent=2)
    logger.info("Wrote %s (%d records), copied %d case DICOMs.", cases_json_path, len(subset), copied_cases)

    if args.skip_opensearch:
        logger.info("Skipping OpenSearch (--skip-opensearch).")
        return

    _load_dotenv_files()
    _ensure_backend_path()

    from app.dicom_processor import load_image
    from app.embedding import EmbeddingService

    os_client = _connect_opensearch()
    embedder = EmbeddingService(args.clip_model)

    per_case: List[Dict[str, Any]] = []
    ref_seen: Set[str] = set()
    unique_refs: Dict[str, Dict[str, Any]] = {}

    for idx, item in enumerate(subset):
        ip = item.get("image_path", "")
        if not ip:
            continue
        full = resolve_path(dicom_root, ip)
        if not full.is_file():
            logger.warning("Case %s: file not found, skip similarity: %s", idx, full)
            per_case.append(
                {
                    "case_index": idx,
                    "query_image_path": ip,
                    "error": "file_not_found",
                    "similar": [],
                }
            )
            continue
        try:
            image = load_image(str(full))
            emb = embedder.embed_image(image).tolist()
        except Exception as e:
            logger.exception("Case %s: embed failed: %s", idx, e)
            per_case.append(
                {
                    "case_index": idx,
                    "query_image_path": ip,
                    "error": str(e),
                    "similar": [],
                }
            )
            continue

        similar = search_similar_by_embedding(
            os_client,
            args.index_name,
            emb,
            args.k_similar,
            exclude_image_paths={ip},
        )
        per_case.append(
            {
                "case_index": idx,
                "query_image_path": ip,
                "similar": similar,
            }
        )

        for doc in similar:
            rpath = doc.get("image_path", "")
            if not rpath or rpath in ref_seen:
                continue
            ref_seen.add(rpath)
            unique_refs[rpath] = {
                "short_description": doc.get("short_description", ""),
                "full_description": doc.get("full_description", ""),
                "opensearch_score_example": doc.get("score"),
                "_id": doc.get("_id"),
            }
            ref_src = resolve_path(dicom_root, rpath)
            ref_dest = ref_dir / Path(rpath).name
            if ref_src.is_file():
                shutil.copy2(ref_src, ref_dest)
            else:
                logger.warning("Reference DICOM not on disk: %s", ref_src)

    report_path = out_dir / "opensearch_similarity_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "index_name": args.index_name,
                "k_similar": args.k_similar,
                "n_cases_requested": args.n_cases,
                "cases_subdir": cases_subdir or None,
                "dicom_root": str(dicom_root),
                "per_case": per_case,
                "unique_references": unique_refs,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    logger.info(
        "Wrote %s (%d per-case blocks, %d unique reference image_paths).",
        report_path,
        len(per_case),
        len(unique_refs),
    )


if __name__ == "__main__":
    main()
