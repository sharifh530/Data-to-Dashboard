import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ProbePolicy:
    """Fixed policy for a future synthetic runtime probe, not user jobs."""

    image: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"(?:[a-z0-9./_-]+@)?sha256:[a-f0-9]{64}", self.image):
            raise ValueError("A reviewed image pinned by sha256 digest is required")

    def command(self, name: str) -> list[str]:
        if not re.fullmatch(r"dtd-probe-[a-f0-9]{32}", name):
            raise ValueError("Invalid server-generated probe name")
        return [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--name",
            name,
            "--runtime=runsc",
            "--network=none",
            "--read-only",
            "--user=65532:65532",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--cpus=2",
            "--memory=2g",
            "--memory-swap=2g",
            "--pids-limit=64",
            "--ulimit=nofile=256:256",
            "--ulimit=core=0:0",
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777",
            "--log-driver=none",
            self.image,
        ]
