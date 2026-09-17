"""Fixed synthetic probe: run ONLY in the dedicated runtime using sandbox:probe.

This file is never imported by the API or test suite. It is not generated code.
"""

import errno
import json
import os
import socket
from pathlib import Path


def cannot_connect(family: int, address: tuple[str, int]) -> bool:
    try:
        with socket.socket(family, socket.SOCK_STREAM) as connection:
            connection.settimeout(0.5)
            connection.connect(address)
    except OSError:
        return True
    return False


def root_is_read_only() -> bool:
    try:
        Path("/opt/dtd-readonly-check").write_text("probe", encoding="utf-8")
    except OSError as error:
        return error.errno == errno.EROFS
    return False


def dns_is_blocked() -> bool:
    # TCP denial alone is not proof of DNS isolation; test resolution separately.
    try:
        socket.getaddrinfo("example.com", 443)
    except OSError:
        return True
    return False


def main() -> None:
    checks = {
        "non_root": os.getuid() == 65532,
        "read_only_root": root_is_read_only(),
        "ipv4_egress_denied": cannot_connect(socket.AF_INET, ("1.1.1.1", 443)),
        "ipv6_egress_denied": cannot_connect(socket.AF_INET6, ("2606:4700:4700::1111", 443)),
        "metadata_denied": cannot_connect(socket.AF_INET, ("169.254.169.254", 80)),
        "dns_denied": dns_is_blocked(),
        "no_runtime_socket": not Path("/var/run/docker.sock").exists(),
        "no_provider_secret": not any(
            key in os.environ
            for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AWS_SECRET_ACCESS_KEY")
        ),
    }
    print(json.dumps({"schema_version": 1, "checks": checks}), flush=True)
    raise SystemExit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
