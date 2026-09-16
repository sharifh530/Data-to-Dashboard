import json
import sys

from dtd_execution.preflight import inspect_runtime

result = inspect_runtime()
print(json.dumps(result.to_dict(), indent=2))
sys.exit(0 if result.runtime_available else 2)
