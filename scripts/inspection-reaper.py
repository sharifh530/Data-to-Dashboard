"""Remove only expired inspector containers. Run by a dedicated systemd timer."""

import json
import re
import subprocess
from datetime import UTC, datetime


def main():
    ids = subprocess.run(
        ["docker", "ps", "-aq", "--filter", "label=dtd.inspector=1"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    ).stdout.split()
    for container in ids[:100]:
        info = json.loads(
            subprocess.run(
                ["docker", "inspect", container],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            ).stdout
        )[0]
        if not re.fullmatch(r"/dtd-probe-[a-f0-9]{32}", info["Name"]):
            continue
        created = datetime.fromisoformat(info["Created"].replace("Z", "+00:00"))
        if (datetime.now(UTC) - created).total_seconds() > 60:
            subprocess.run(
                ["docker", "rm", "--force", container],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )


if __name__ == "__main__":
    main()
