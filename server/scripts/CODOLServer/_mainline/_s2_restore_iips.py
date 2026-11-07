# -*- coding: utf-8 -*-
"""S2-L: restore the pristine baseline iips.dll into the working sandbox.

Backs up the current file first. Pure file operation, no net changes.
"""
import os, sys, shutil, hashlib, json, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
BASELINE = os.path.join(ROOT, "工具", "EX035_DIR", "IIPS", "iips.dll")
SANDBOX = os.path.join(ROOT, "run_codol_001", "sandbox_ifs1_20260923")
TARGETS = [
    os.path.join(SANDBOX, "IIPS", "iips.dll"),
    os.path.join(ROOT, "COD OL", "IIPS", "iips.dll"),
]
BACKUP_DIR = os.path.join(ROOT, "backups",
                          "S2_IIPS_RESTORE_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def main():
    apply = "--apply" in sys.argv
    os.makedirs(BACKUP_DIR, exist_ok=True)
    rep = {"baseline": {"path": BASELINE, "sha": sha(BASELINE)},
           "backup_dir": BACKUP_DIR, "targets": [], "applied": apply}
    for t in TARGETS:
        if not os.path.exists(t):
            rep["targets"].append({"path": t, "status": "missing"})
            continue
        before = sha(t)
        rec = {"path": t, "sha_before": before,
               "already_baseline": before == rep["baseline"]["sha"]}
        if apply and not rec["already_baseline"]:
            bkp = os.path.join(BACKUP_DIR,
                               os.path.basename(os.path.dirname(t)) + "_" + os.path.basename(t))
            shutil.copy2(t, bkp)
            shutil.copy2(BASELINE, t)
            rec["sha_after"] = sha(t)
            rec["backup"] = bkp
            rec["status"] = "restored"
        elif apply:
            rec["status"] = "already_baseline"
        else:
            rec["status"] = "dry-run"
        rep["targets"].append(rec)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    with open(os.path.join(BACKUP_DIR, "restore_report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
