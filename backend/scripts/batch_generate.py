"""
Batch runner to generate descriptions for all DICOM cases in a directory and
save outputs (descriptions, scores, retrieved cases, validation info) to JSON.
"""

import argparse
import json
import logging
from pathlib import Path
from typing import List

from app.rag_pipeline import get_rag_pipeline

logger = logging.getLogger(__name__)


def collect_dicom_files(input_dir: Path) -> List[Path]:
    """Return a sorted list of DICOM files under input_dir."""
    patterns = ["*.dcm", "*.dicom"]
    files: List[Path] = []
    for pat in patterns:
        files.extend(input_dir.rglob(pat))
    return sorted(set(files))


def _write_results(results: List[dict], output_file: Path) -> None:
    """Write results atomically to avoid partial files."""
    tmp_path = output_file.with_suffix(output_file.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    tmp_path.replace(output_file)


def _load_existing_results(output_file: Path) -> List[dict]:
    """Load previously saved results to allow resuming interrupted runs."""
    if not output_file.exists():
        return []

    try:
        with output_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            logger.warning(
                f"Existing output {output_file} is not a JSON list. Ignoring it."
            )
            return []
        logger.info(f"Loaded {len(data)} existing results from {output_file}")
        return data
    except Exception as exc:
        logger.warning(
            f"Could not read existing output {output_file}: {exc}. Starting fresh."
        )
        return []


def run_batch(
    input_dir: Path,
     output_file: Path,
    use_retrieved_images: bool,
    flush_every: int,
) -> None:
    pipeline = get_rag_pipeline()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    results = _load_existing_results(output_file)
    processed_paths = {
        item.get("relative_path")
        for item in results
        if isinstance(item, dict) and item.get("relative_path")
    }

    dicom_files = collect_dicom_files(input_dir)
    if not dicom_files:
        logger.warning(f"No DICOM files found under {input_dir}")
        return

    total = len(dicom_files)
    to_process = [
        path for path in dicom_files if str(path.relative_to(input_dir)) not in processed_paths
    ]
    skipped = total - len(to_process)
    logger.info(
        f"Found {total} files. "
        f"Skipping {skipped} already processed. "
        f"Processing {len(to_process)} files..."
    )

    if not to_process:
        logger.info("Nothing to do; all files are already processed.")
        return

    process_total = len(to_process)
    for idx, path in enumerate(to_process, 1):
        relative_path = str(path.relative_to(input_dir))
        try:
            image_bytes = path.read_bytes()
            res = pipeline.process_query(
                image_bytes=image_bytes,
                filename=path.name,
                use_retrieved_images=use_retrieved_images,
                clear_context=True,
            )

            results.append(
                {
                    "filename": path.name,
                    "relative_path": relative_path,
                    "generated_description": res.get("generated_description"),
                    "quality_score": res.get("quality_score"),
                    "quality_approved": res.get("quality_approved"),
                    "retrieved_documents": res.get("retrieved_documents"),
                    "validation_info": res.get("validation_info"),
                    "prompt_used": res.get("prompt_used"),
                    "message": res.get("message"),
                }
            )
            logger.info(
                f"[{idx}/{process_total}] Processed {path.name} "
                f"(approved={res.get('quality_approved')}, score={res.get('quality_score')})"
            )
        except Exception as exc:
            logger.error(f"Failed to process {path}: {exc}")
            results.append(
                {
                    "filename": path.name,
                    "relative_path": relative_path,
                    "generated_description": "",
                    "quality_score": None,
                    "quality_approved": False,
                    "retrieved_documents": [],
                    "validation_info": None,
                    "prompt_used": None,
                    "message": f"Error: {exc}",
                }
            )

        # Periodic flush with simple progress indicator
        if idx % flush_every == 0 or idx == process_total:
            percent = (idx / process_total) * 100
            logger.info(
                f"Flushing progress: {idx}/{process_total} ({percent:.1f}%) to {output_file}"
            )
            _write_results(results, output_file)

    logger.info(f"Completed. Wrote {len(results)} results to {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate descriptions for all DICOM cases in a directory."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/test"),
        help="Directory containing DICOM files (default: data/test)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/test_outputs.json"),
        help="Path to output JSON (default: data/test_outputs.json)",
    )
    parser.add_argument(
        "--use-retrieved-images",
        action="store_true",
        help="Include retrieved images in the GPT prompt.",
    )
    parser.add_argument(
        "--flush-every",
        type=int,
        default=20,
        help="Write intermediate JSON every N files (default: 20).",
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    run_batch(
        input_dir=args.input_dir,
        output_file=args.output,
        use_retrieved_images=args.use_retrieved_images,
        flush_every=max(1, args.flush_every),
    )


if __name__ == "__main__":
    main()
