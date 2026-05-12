"""CLI for evaluating generated image/video outputs against reference inputs.

Run from repo root:
    python scripts/run_gen_eval.py \\
        --refs ref1.png ref2.png \\
        --gen-output output.png \\
        --prompt "Put the person in image 1 on the sofa in image 2"

Output type (image vs video) is detected automatically from the --gen-output extension.
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

from qwen_vl import QwenVL          # noqa: E402
from gen_eval import RefConsistencyEval, PromptAdherenceEval  # noqa: E402

LOGGER = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a generated image/video output against reference inputs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/run_gen_eval.py \\\n"
            "    --refs ref1.png ref2.png \\\n"
            "    --gen-output output.png \\\n"
            "    --prompt \"Put the person in image 1 on the sofa in image 2\"\n\n"
            "  python scripts/run_gen_eval.py \\\n"
            "    --refs ref.png \\\n"
            "    --gen-output output.mp4 \\\n"
            "    --prompt \"Animate this character walking\""
        ),
    )
    parser.add_argument(
        "--refs",
        nargs="+",
        required=True,
        metavar="PATH_OR_URL",
        help="One or more reference image paths or URLs used during generation.",
    )
    parser.add_argument(
        "--gen-output",
        required=True,
        metavar="PATH_OR_URL",
        help="Path or URL of the generated output (image or video) to evaluate.",
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help="The user prompt that was used to produce the generated output.",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help="Override model path or HF repo ID (default: QwenVL default).",
    )
    parser.add_argument(
        "--ref-coherence",
        action="store_true",
        help="Run reference consistency evaluation.",
    )
    parser.add_argument(
        "--prompt-adherence",
        action="store_true",
        help="Run prompt adherence evaluation.",
    )
    parser.add_argument(
        "--non-prompt-artifact",
        action="store_true",
        help="Run unprompted artifact check (not yet implemented).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all evaluations (default when no eval flag is specified).",
    )
    args = parser.parse_args(argv)
    if not args.prompt.strip():
        parser.error("--prompt must be non-empty.")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    run_all = args.all or not any([args.ref_coherence, args.prompt_adherence, args.non_prompt_artifact])
    run_ref = run_all or args.ref_coherence
    run_pa  = run_all or args.prompt_adherence
    run_npa = run_all or args.non_prompt_artifact

    print("Loading model (this may take a moment)...")
    kwargs: dict = {}
    if args.model_id:
        kwargs["model_id"] = args.model_id
    runner = QwenVL(**kwargs)

    evaluator_ref = RefConsistencyEval()
    evaluator_pa  = PromptAdherenceEval()
    result: dict = {}

    # ── ref consistency ───────────────────────────────────────────────────────
    if run_ref:
        print("\nChecking whether reference consistency evaluation is required...")
        try:
            check = evaluator_ref.ref_comf_required_check(
                runner=runner,
                ref_paths=args.refs,
                user_prompt=args.prompt,
                output_path=args.gen_output,
            )
        except (ValueError, RuntimeError) as exc:
            print(f"Error during consistency check: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc

        print(f"Consistency required: {check['required']}")
        print(f"Reasoning: {check['reasoning']}")
        result["ref_consistency"] = dict(check)

        if check["required"]:
            print("\nRunning reference consistency scoring...")
            try:
                eval_result = evaluator_ref.ref_consistency_eval(
                    runner=runner,
                    ref_paths=args.refs,
                    user_prompt=args.prompt,
                    output_path=args.gen_output,
                    prior_analysis=check["reasoning"],
                )
            except (ValueError, RuntimeError) as exc:
                print(f"Error during consistency eval: {exc}", file=sys.stderr)
                raise SystemExit(1) from exc
            print(f"Consistency score: {eval_result['score']}/5")
            print(f"Reasoning: {eval_result['reasoning']}")
            result["ref_consistency"].update(eval_result)
        else:
            print("Reference consistency scoring not required — skipping.")

    # ── prompt adherence ──────────────────────────────────────────────────────
    if run_pa:
        print("\nRunning prompt adherence evaluation...")
        try:
            pa_result = evaluator_pa.prompt_adherence_eval(
                runner=runner,
                ref_paths=args.refs,
                user_prompt=args.prompt,
                output_path=args.gen_output,
            )
        except (ValueError, RuntimeError) as exc:
            print(f"Error during prompt adherence eval: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        print(f"Prompt adherence score: {pa_result['score']}/5")
        print(f"Reasoning: {pa_result['reasoning']}")
        result["prompt_adherence"] = pa_result

    # ── non-prompt artifact ───────────────────────────────────────────────────
    if run_npa:
        print("\nNon-prompt artifact check: not yet implemented — skipping.")
        result["non_prompt_artifact"] = {"status": "not_implemented"}

    print("\n--- Result ---")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
