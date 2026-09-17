"""Fixed bounded resource exercises. Run ONLY inside the dedicated gVisor runtime."""

import errno
import json
import os
import signal
import sys
import time


def main() -> None:
    mode = sys.argv[1]
    if mode == "memory":
        blocks = []
        for _ in range(512):
            blocks.append(bytearray(1024 * 1024))
        raise SystemExit("Memory cap did not stop 512 MiB allocation")
    if mode == "disk":
        try:
            with open("/tmp/fill", "wb", buffering=0) as file:
                for _ in range(16):
                    file.write(b"x" * 1024 * 1024)
        except OSError as error:
            print(json.dumps({"disk_full": error.errno == errno.ENOSPC}), flush=True)
            return
        raise SystemExit("Scratch cap did not stop 16 MiB write")
    if mode == "pids":
        children = []
        try:
            for _ in range(96):
                try:
                    pid = os.fork()
                except OSError as error:
                    print(
                        json.dumps(
                            {"pids_limited": error.errno == errno.EAGAIN, "children": len(children)}
                        ),
                        flush=True,
                    )
                    return
                if pid == 0:
                    time.sleep(20)
                    os._exit(0)
                children.append(pid)
            raise SystemExit("Process cap did not stop 96 forks")
        finally:
            for pid in children:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
    if mode == "output":
        for _ in range(4096):
            os.write(1, b"x" * 4096)
        time.sleep(20)
        return
    if mode in {"cpu", "cancel", "timeout"}:
        for _ in range(3):
            if os.fork() == 0:
                while True:
                    pass
        print(json.dumps({"ready": True, "children": 3}), flush=True)
        while True:
            pass
    raise SystemExit("Unsupported fixed exercise")


if __name__ == "__main__":
    main()
