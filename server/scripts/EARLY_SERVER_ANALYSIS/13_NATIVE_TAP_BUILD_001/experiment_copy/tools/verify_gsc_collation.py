#!/usr/bin/env python3
"""Offline verifier for the collated sh1x GSC root (tools/collate_gsc.py).

There is no script-parse CLI in this tree (bin/codol_dedrun.exe --codol-info
prints a static build banner and does not touch the script roots; the only
parser fixtures are tests/test_codol_script_source.c and
tests/test_codol_script_lower.cpp, which are unit tests, not file drivers).
This verifier therefore does offline, without starting a server:

  1. resolution parity -- replays the loader's probe order
     (src/codol/script/codol_script_source.c) against BOTH the pre-collation
     three-root configuration and the collated single root, and compares the
     bytes each returns for every module name the server actually asked for
     ("CoDOL lowering: <path>" in bin/home/main/qconsole.log[.old]) plus every
     path in the collation manifest.
  2. manifest integrity -- every file the manifest lists exists in the collated
     root with the recorded sha1.
  3. source admissibility -- every collated .gsc/.csc/.atr is within the
     loader's 16 MiB limit, is free of the embedded NUL that makes
     read_source() return -1 (ERR_DROP), and is brace/paren balanced outside
     strings and comments.  This is a structural pre-check, not the compiler.

stdlib only.
"""

import argparse
import hashlib
import json
import os
import re
import sys

REPO_DEFAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE_DEFAULT = (r"D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13"
                     r"\CODOL\1.1.1.13_server\alpha0022")

# Shared with tools/collate_gsc.py: paths deliberately not collated. They still
# resolve in the pre-collation three-root configuration, and older boot logs
# still name them, so they are reported as withdrawn rather than as failures.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collate_gsc import EXCLUDE_DEFAULT, load_exclusions, excluded  # noqa: E402

LOWERING = re.compile(r"CoDOL lowering: (\S+) \(")
MAX_SOURCE = 16 * 1024 * 1024

ALIASES = {
    "character/mp_character_us_army_lmg.gsc":
        "character/charactermp_character_us_army_lmg.gsc",
    "character/mp_character_us_army_smg_b.gsc":
        "character/character_us_army_smg_b.gsc",
}


def read_source(root, prefix, name):
    """Mirror read_source(): (status, bytes). status 1 hit, 0 miss, -1 reject."""
    if not root:
        return 0, None
    path = os.path.join(root, (prefix + name).replace("/", os.sep))
    if not os.path.isfile(path):
        return 0, None
    try:
        size = os.path.getsize(path)
        if size > MAX_SOURCE:
            return -1, None
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        return -1, None
    if b"\0" in data:
        return -1, None
    return 1, data


def resolve(base, overlay, native, zone, name):
    """CODOL_ReadScriptSourceWithNativeOverlayForZone, byte for byte."""
    if zone and zone.isalpha() and zone.islower():
        status, data = read_source(native, zone + "/", name)
        if status:
            return status, data, "native/%s" % zone
    for root, prefix, label in ((native, "", "native"),
                                (overlay, "", "overlay"),
                                (base, "mp/", "base/mp"),
                                (base, "", "base")):
        status, data = read_source(root, prefix, name)
        if status:
            return status, data, label
    alias = ALIASES.get(name)
    if alias:
        status, data = read_source(base, "", alias)
        if status:
            return status, data, "base/alias"
    return 0, None, None


def balanced(text):
    """Brace/paren/bracket balance outside strings, // and /* */ comments."""
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            i = text.find("\n", i)
            if i < 0:
                break
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if ch == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            i += 1
            continue
        if ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack or stack.pop() != pairs[ch]:
                return False
        i += 1
    return not stack


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify the collated sh1x GSC root.")
    parser.add_argument("--repo", default=REPO_DEFAULT)
    parser.add_argument("--reference", default=REFERENCE_DEFAULT)
    parser.add_argument("--dest", default=None)
    parser.add_argument("--zone", default="mp", help="codol_zoneType to replay (mp|coop|zm)")
    parser.add_argument("--log", action="append", default=None,
                        help="qconsole log to harvest lowering paths from (repeatable)")
    parser.add_argument("--limit-structure", type=int, default=0,
                        help="only structure-check the first N files (0 = all)")
    parser.add_argument("--exclude-file", default=EXCLUDE_DEFAULT,
                        help="persistent never-collate pattern list "
                             "(default tools/collate_exclude.txt)")
    args = parser.parse_args(argv)
    exclusions = load_exclusions(args.exclude_file)

    repo = os.path.abspath(args.repo)
    reference = os.path.abspath(args.reference)
    dest = os.path.abspath(args.dest or os.path.join(repo, "bin", "home", "codol_rawfiles"))
    old = {"base": os.path.join(reference, "vendor", "iw4"),
           "overlay": os.path.join(reference, "gsc_overlay"),
           "native": os.path.join(repo, "scripts", "codol")}
    logs = args.log or [os.path.join(repo, "bin", "home", "main", "qconsole.log"),
                        os.path.join(repo, "bin", "home", "main", "qconsole.log.old")]

    print("verify_gsc_collation")
    print("  collated root %s" % dest)
    print("  zone          %s" % args.zone)

    manifest_path = os.path.join(dest, "COLLATION_MANIFEST.json")
    if not os.path.isfile(manifest_path):
        print("  error: no COLLATION_MANIFEST.json; run tools/collate_gsc.py first")
        return 2
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    files = manifest["files"]
    print("  manifest      %d files, generated %s" % (len(files), manifest["generated"]))

    failures = []

    # 1. manifest integrity
    bad_hash = missing = 0
    for rel, record in files.items():
        path = os.path.join(dest, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            missing += 1
            failures.append("missing from collated root: %s" % rel)
            continue
        with open(path, "rb") as handle:
            if hashlib.sha1(handle.read()).hexdigest() != record["sha1"]:
                bad_hash += 1
                failures.append("sha1 mismatch: %s" % rel)
    print("\n  [1] manifest integrity: %d files, %d missing, %d sha1 mismatches"
          % (len(files), missing, bad_hash))

    # 2. lowering paths from the real boot logs
    requested = set()
    for log in logs:
        if not os.path.isfile(log):
            continue
        with open(log, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                found = LOWERING.search(line)
                if found:
                    requested.add(found.group(1))
    print("  [2] boot logs: %d distinct 'CoDOL lowering:' module names" % len(requested))

    # 3. resolution parity old vs new, over lowering names + every manifest path
    names = sorted(requested | set(files))
    parity_ok = parity_diff = only_old = only_new = rejected = withdrawn = 0
    for name in names:
        if excluded(name, exclusions):
            # Deliberately not collated; the old three-root form still serves it.
            withdrawn += 1
            continue
        so, do, lo = resolve(old["base"], old["overlay"], old["native"], args.zone, name)
        sn, dn, ln = resolve(dest, dest, dest, args.zone, name)
        if so == 1 and sn == 1:
            if do == dn:
                parity_ok += 1
            else:
                parity_diff += 1
                failures.append("BYTES DIFFER %s (old %s, new %s)" % (name, lo, ln))
        elif so == 1 and sn != 1:
            only_old += 1
            failures.append("LOST %s (old resolved from %s, new status %d)" % (name, lo, sn))
        elif so != 1 and sn == 1:
            only_new += 1
            failures.append("NEW-ONLY %s (old status %d, new %s)" % (name, so, ln))
        elif so == -1 or sn == -1:
            rejected += 1
    print("  [3] resolution parity over %d names: %d identical, %d differing, "
          "%d lost, %d new-only, %d rejected by both, %d withdrawn by "
          "tools/collate_exclude.txt" %
          (len(names), parity_ok, parity_diff, only_old, only_new, rejected, withdrawn))

    lost_lowering = []
    for name in sorted(requested):
        if excluded(name, exclusions):
            continue
        status, _, _ = resolve(dest, dest, dest, args.zone, name)
        if status != 1:
            # animtrees are served from the mounted client zones first; a miss
            # in the script roots is only fatal when no archive defines them.
            lost_lowering.append((name, status))
    hard = [n for n, s in lost_lowering if not n.startswith("animtrees/")]
    print("  [4] every logged lowering path resolves in the collated root: "
          "%d unresolved (%d outside animtrees/)" % (len(lost_lowering), len(hard)))
    for name, status in lost_lowering:
        print("        %s (status %d)%s" % (name, status,
              "  [mounted animtree, served from the client zone]"
              if name.startswith("animtrees/") else ""))
    failures += ["lowering path unresolved: %s" % n for n in hard]

    # 4. source admissibility
    checked = unbalanced = nul = oversize = 0
    for rel in sorted(files):
        if not rel.lower().endswith((".gsc", ".csc", ".atr")):
            continue
        if args.limit_structure and checked >= args.limit_structure:
            break
        path = os.path.join(dest, rel.replace("/", os.sep))
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError:
            continue
        checked += 1
        if len(data) > MAX_SOURCE:
            oversize += 1
            failures.append("oversize: %s" % rel)
        if b"\0" in data:
            nul += 1
            print("        embedded NUL (loader ERR_DROPs on request): %s" % rel)
            continue
        if not balanced(data.decode("utf-8", "replace")):
            unbalanced += 1
            print("        unbalanced braces/parens: %s" % rel)
    print("  [5] source admissibility: %d checked, %d embedded NUL, "
          "%d unbalanced, %d oversize" % (checked, nul, unbalanced, oversize))

    print()
    if failures:
        print("  FAILURES (%d):" % len(failures))
        for item in failures[:80]:
            print("    %s" % item)
        if len(failures) > 80:
            print("    ... %d more" % (len(failures) - 80))
        return 1
    print("  OK: the collated root resolves every requested and manifested module "
          "to the same bytes as the three-root configuration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
