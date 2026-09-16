import argparse
import json

from dtd_execution.probe import run_probe

parser = argparse.ArgumentParser(description="Run only the reviewed synthetic isolation image")
parser.add_argument("--image", required=True, help="Reviewed synthetic probe image@sha256:digest")
args = parser.parse_args()
try:
    result = run_probe(args.image)
except (RuntimeError, ValueError, OSError) as error:
    print(
        json.dumps(
            {"status": "blocked_or_failed", "reason": str(error), "execution_enabled": False}
        )
    )
    raise SystemExit(2) from None
print(json.dumps(result, indent=2))
