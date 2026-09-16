import argparse
import json
from pathlib import Path

from dtd_api.contracts import RunCreate
from dtd_api.main import create_app

parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1] / "packages" / "contracts"
documents = {
    "openapi.json": create_app().openapi(),
    "run-create.schema.json": RunCreate.model_json_schema(),
}
for name, document in documents.items():
    serialized = json.dumps(document, indent=2, sort_keys=True) + "\n"
    target = root / name
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != serialized:
            raise SystemExit(f"Contract drift: {name}; run npm run contracts:generate")
    else:
        root.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized, encoding="utf-8")
print("Contracts checked." if args.check else "Contracts generated.")
