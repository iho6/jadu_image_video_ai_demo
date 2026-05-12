"""CLI for batch-evaluating Jadu QC results using gen eval.

Run from repo root:
    python scripts/run_batch_gen_eval.py \\
        --input input/jadu_qc_results/qc_results.json \\
        --limit 10

    python scripts/run_batch_gen_eval.py \\
        --input input/jadu_qc_results/qc_results_video.json \\
        --limit 5 \\
        --vs-jadu-eval
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT), str(_ROOT / "code")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gen_eval import RefConsistencyEval  # noqa: E402
from qwen_vl import QwenVL              # noqa: E402
from utils.jadu_data_processor import load_entries  # noqa: E402

LOGGER = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch-evaluate Jadu QC results using gen eval.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/run_batch_gen_eval.py \\\n"
            "    --input input/jadu_qc_results/qc_results.json \\\n"
            "    --limit 10\n\n"
            "  python scripts/run_batch_gen_eval.py \\\n"
            "    --input input/jadu_qc_results/qc_results_video.json \\\n"
            "    --limit 5 \\\n"
            "    --vs-jadu-eval"
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="PATH",
        help="Path to a Jadu QC results JSON file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of evaluable entries to process (default: all).",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help="Override model path or HF repo ID (default: QwenVL default).",
    )
    parser.add_argument(
        "--vs-jadu-eval",
        action="store_true",
        help="Include Jadu's original QA fields alongside the gen eval result.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    entries = load_entries(args.input, limit=args.limit)
    total = len(entries)
    print(f"Loaded {total} evaluable entries from {args.input}", file=sys.stderr)

    if not entries:
        print("[]")
        return

    kwargs: dict = {}
    if args.model_id:
        kwargs["model_id"] = args.model_id
    print("Loading model (this may take a moment)...", file=sys.stderr)
    runner = QwenVL(**kwargs)
    evaluator = RefConsistencyEval()

    results = []
    for i, entry in enumerate(entries, 1):
        job_id = entry["job_id"]
        print(f"[{i}/{total}] job_id={job_id}", file=sys.stderr)

        check = evaluator.ref_comf_required_check(
            runner=runner,
            ref_paths=entry["refs"],
            user_prompt=entry["prompt"],
            output_path=entry["output"],
        )
        ref_consistency: dict = {
            "response": check["response"],
            "reasoning": check["reasoning"],
        }

        if check["response"]:
            eval_result = evaluator.ref_consistency_eval(
                runner=runner,
                ref_paths=entry["refs"],
                user_prompt=entry["prompt"],
                output_path=entry["output"],
                prior_analysis=check["reasoning"],
            )
            ref_consistency["score"] = eval_result["score"]
            ref_consistency["score_reasoning"] = eval_result["reasoning"]

        result: dict = {"job_id": job_id, "ref_consistency": ref_consistency}
        if args.vs_jadu_eval:
            result["jadu_qa"] = entry["jadu_qa"]

        results.append(result)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
