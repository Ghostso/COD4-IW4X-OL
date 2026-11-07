"""Keep isolated native-server probes out of an active human C1 session."""

import subprocess


def refuse_parallel_game():
    result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
                            text=True, check=True)
    names = {line.split(",", 1)[0].strip('"').lower() for line in result.stdout.splitlines()}
    active = sorted(name for name in names if name == "c1.exe" or name.startswith("codol_dedrun"))
    if active:
        raise RuntimeError("isolated server probe refused while a human client or dedicated server is running: "
                           + ", ".join(active))
