#!/usr/bin/env python3
"""Collate every GSC source root the sh1x server resolves into one tree.

The native loader (src/cscr_parser.cpp Scr_ReadFile ->
src/codol/script/codol_script_source.c CODOL_ReadScriptSourceWithNativeOverlayForZone)
resolves a requested script module name against three roots, in this order:

    1. <codol_scriptNativeOverlay>/<zoneType>/<name>   (zoneType = mp|coop|zm)
    2. <codol_scriptNativeOverlay>/<name>
    3. <codol_scriptOverlay>/<name>
    4. <codol_scriptPath>/mp/<name>
    5. <codol_scriptPath>/<name>
    6. two exact filename aliases under <codol_scriptPath>
       (docs/CODOL_SCRIPT_EXPORT_FILENAMES.md)

This tool merges those roots into one directory at the SAME relative paths,
highest precedence winning, so the server can run with all three dvars pointed
at the single collated root.  Because every probe keeps its relative path
(including the "mp/" and "<zoneType>/" prefixes, which are NOT flattened), the
collated root resolves each name to exactly the bytes the three-root form did.

Copy set
--------
Only files the server can actually load through a script root are copied:

    .gsc  script modules                (Scr_ReadFile, demand driven)
    .csc  client script modules         (same reader, none ship today)
    .atr  animation trees               (Scr_ReadFile animtrees/ fallthrough,
                                         used only when no mounted archive
                                         defines the tree)
    .csv  string tables                 (CODOL_LoadReferenceStringTable via
                                         codol_scriptPath -- db_load.cpp,
                                         codol_script_unlock.c,
                                         codol_asset_commands.c)
    .def  structured-data schemas       (carried for redistribution; the loader
                                         reads .def from mounted client zones,
                                         not from a script root)

Everything else in a root (.menu, .vision, .cfg, .rmb, .graph, .arena,
weapon files, ...) is client/zone content that never reaches a script root, and
is not copied.  Files already in the destination whose extension is outside the
copy set are never touched or deleted -- that is where the developer rawfile
dump (FS_SV_HomeWriteFile "codol_rawfiles/%s") keeps the client's own shipped
rawfiles.

"Being used"
------------
Script resolution is demand driven: there is no manifest, and the requested
names come from #include, precache, per-map level scripts, per-character and
per-weapon module names generated at runtime.  A single boot's
"CoDOL lowering: <path>" list is therefore a lower bound for one map/gametype,
not the reachable set.  The rule this tool implements: carry the FULL vendor
tree, filtered to the loadable extensions above, because any name can be
requested and a miss falls through to the fastfile/rawfile path.

Exclusions
----------
tools/collate_exclude.txt lists module paths this tool must never collate, so a
subtree that CoDOL has replaced cannot be resurrected from a source root by the
next run.  Excluded paths are dropped before precedence is resolved, and any
copy already sitting in the destination is pruned (subject to the same
byte-attribution rule as an ordinary prune).  tools/verify_gsc_collation.py
reads the same file and does not count an excluded path as a lost resolution.

Idempotent: re-running copies only files whose content differs, and prunes
files this tool previously wrote that no longer exist in any root (tracked by
the manifest; a file whose bytes no longer match the manifest is left alone).

stdlib only.
"""

import argparse
import datetime
import fnmatch
import hashlib
import json
import os
import shutil
import sys

# Lowest precedence first.  Order matters: later roots override earlier ones.
ROOT_ORDER = ("vendor", "overlay", "native")

LOADABLE_EXT = (".gsc", ".csc", ".atr", ".csv", ".def")

MANIFEST_NAME = "COLLATION_MANIFEST.json"
CONFLICTS_NAME = "COLLATION_CONFLICTS.txt"
# Never treated as collated payload even if the extension matched.
RESERVED = {MANIFEST_NAME.lower(), CONFLICTS_NAME.lower()}

REPO_DEFAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE_DEFAULT = (r"D:\CoD\CODOL Builds\Call of Duty Online 1.1.1.13"
                     r"\CODOL\1.1.1.13_server\alpha0022")

# Persistent "never collate this" list, shared with verify_gsc_collation.py so
# an intentionally dropped subtree is not reported as a resolution regression.
EXCLUDE_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "collate_exclude.txt")

MAX_SOURCE = 16 * 1024 * 1024  # read_source() in codol_script_source.c


def load_exclusions(path):
    """-> list of lowercase patterns; missing file means "exclude nothing"."""
    patterns = []
    if not path or not os.path.isfile(path):
        return patterns
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.split("#", 1)[0].strip().replace("\\", "/").lower()
            if line:
                patterns.append(line)
    return patterns


def excluded(rel, patterns):
    """Match a loader-relative module path against the exclusion patterns.

    A pattern beginning with '!' is a keep: it re-includes a path an earlier
    directory exclusion swept up, so a single needed file does not force a
    whole directory tree back into the collation.  Keeps are checked first, so
    their position in the file does not matter.
    """
    low = rel.lower()

    def matches(pattern):
        if pattern.endswith("/**"):
            return low.startswith(pattern[:-2])
        return fnmatch.fnmatchcase(low, pattern)

    for pattern in patterns:
        if pattern.startswith("!") and matches(pattern[1:]):
            return None
    for pattern in patterns:
        if pattern.startswith("!"):
            continue
        if matches(pattern):
            return pattern
    return None


def sha1_bytes(data):
    return hashlib.sha1(data).hexdigest()


def read_file(path):
    with open(path, "rb") as handle:
        return handle.read()


def legal_module_name(rel):
    """Mirror the traversal/charset rules CODOL_ReadScriptSource* enforces."""
    if not rel:
        return False
    for ch in rel:
        if ch in ("\\", ":") or ord(ch) >= 128:
            return False
    for segment in rel.split("/"):
        if not segment or segment in (".", ".."):
            return False
    return True


def scan_root(root):
    """rel path -> absolute path, for every loadable file under root."""
    found = {}
    if not root or not os.path.isdir(root):
        return found
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            if not name.lower().endswith(LOADABLE_EXT):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel.lower() in RESERVED:
                continue
            if not legal_module_name(rel):
                print("  skip (illegal module name): %s" % rel)
                continue
            found[rel] = full
    return found


def load_manifest(path):
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (ValueError, OSError):
        return {}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Collate the sh1x GSC source roots into one redistributable tree.")
    parser.add_argument("--repo", default=REPO_DEFAULT,
                        help="IW4OL_Server repository root")
    parser.add_argument("--reference", default=REFERENCE_DEFAULT,
                        help="alpha0022 reference root (holds vendor/iw4 and gsc_overlay)")
    parser.add_argument("--vendor", default=None, help="override codol_scriptPath root")
    parser.add_argument("--overlay", default=None, help="override codol_scriptOverlay root")
    parser.add_argument("--native", default=None, help="override codol_scriptNativeOverlay root")
    parser.add_argument("--dest", default=None,
                        help="collated root (default <repo>/bin/home/codol_rawfiles)")
    parser.add_argument("--dry-run", action="store_true",
                        help="report only; write nothing")
    parser.add_argument("--no-prune", action="store_true",
                        help="keep files this tool wrote that no longer exist in any root")
    parser.add_argument("--exclude-file", default=EXCLUDE_DEFAULT,
                        help="persistent never-collate pattern list "
                             "(default tools/collate_exclude.txt)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    repo = os.path.abspath(args.repo)
    reference = os.path.abspath(args.reference)
    roots = {
        "vendor": os.path.abspath(args.vendor or os.path.join(reference, "vendor", "iw4")),
        "overlay": os.path.abspath(args.overlay or os.path.join(reference, "gsc_overlay")),
        "native": os.path.abspath(args.native or os.path.join(repo, "scripts", "codol")),
    }
    dest = os.path.abspath(args.dest or os.path.join(repo, "bin", "home", "codol_rawfiles"))

    exclusions = load_exclusions(args.exclude_file)

    print("sh1x GSC collation")
    for name in ROOT_ORDER:
        state = "ok" if os.path.isdir(roots[name]) else "MISSING"
        print("  %-8s %-6s %s" % (name, state, roots[name]))
    print("  dest            %s" % dest)
    print("  exclusions      %d pattern(s) from %s"
          % (len(exclusions), args.exclude_file))
    print()

    missing = [n for n in ROOT_ORDER if not os.path.isdir(roots[n])]
    if "vendor" in missing:
        # 2026-09-16: the alpha0022 vendor tree was retired by the user. The
        # previously collated root already carries the full vendor set, so
        # when the vendor root is absent collate FROM the current dest: it
        # becomes the vendor layer and the overlay/native roots re-apply on top.
        # Files removed from an overlay since the last run are NOT pruned in
        # this mode (there is no vendor copy to fall back to); re-point --vendor
        # at a real vendor tree to get a clean rebuild.
        if os.path.isdir(dest):
            print("note: vendor root missing; using the existing collated root %s as the vendor layer" % dest)
            roots["vendor"] = dest
            missing = [n for n in missing if n != "vendor"]
        else:
            print("error: vendor root not found: %s" % roots["vendor"])
            return 2

    scans = {}
    for name in ROOT_ORDER:
        scans[name] = scan_root(roots[name])
        print("  scanned %-8s %5d loadable files" % (name, len(scans[name])))

    # Winner per relative path, plus every lower root that also had it.
    # An excluded path is dropped here, before any root can win it, so the
    # subtree never reappears no matter which root still ships it.
    winners = {}
    excluded_paths = {}
    for name in ROOT_ORDER:  # ascending precedence: later assignment wins
        for rel, full in scans[name].items():
            pattern = excluded(rel, exclusions)
            if pattern:
                excluded_paths[rel] = pattern
                continue
            winners[rel] = name
    if excluded_paths:
        by_pattern = {}
        for pattern in excluded_paths.values():
            by_pattern[pattern] = by_pattern.get(pattern, 0) + 1
        for pattern in sorted(by_pattern):
            print("  excluded %-10s %5d source file(s)" % (pattern, by_pattern[pattern]))

    manifest_path = os.path.join(dest, MANIFEST_NAME)
    previous = load_manifest(manifest_path)
    previous_files = previous.get("files", {}) if isinstance(previous, dict) else {}

    files = {}
    conflicts = []
    case_index = {}
    case_collisions = []
    counts = {"copied": 0, "updated": 0, "unchanged": 0, "failed": 0,
              "pruned": 0, "conflicts": 0, "excluded": len(excluded_paths)}
    by_root = {name: 0 for name in ROOT_ORDER}
    warnings = []

    for rel in sorted(winners):
        winner = winners[rel]
        src = scans[winner][rel]
        try:
            data = read_file(src)
        except OSError as exc:
            print("  FAILED read %s (%s)" % (src, exc))
            counts["failed"] += 1
            continue

        digest = sha1_bytes(data)
        if len(data) > MAX_SOURCE:
            warnings.append("%s exceeds the loader's 16 MiB source limit (%d bytes)"
                            % (rel, len(data)))
        if b"\0" in data and rel.lower().endswith((".gsc", ".csc", ".atr")):
            warnings.append("%s contains an embedded NUL; the loader rejects it "
                            "with ERR_DROP when requested" % rel)

        # Lower roots that also provide this path.
        shadowed = []
        for other in ROOT_ORDER:
            if other == winner:
                continue
            if ROOT_ORDER.index(other) > ROOT_ORDER.index(winner):
                continue  # cannot happen: winner is the highest
            if rel not in scans[other]:
                continue
            try:
                other_digest = sha1_bytes(read_file(scans[other][rel]))
            except OSError:
                other_digest = None
            shadowed.append({"root": other, "path": scans[other][rel],
                             "sha1": other_digest,
                             "identical": other_digest == digest})
        if shadowed:
            counts["conflicts"] += 1
            conflicts.append({"path": rel, "winner": winner,
                              "winner_path": src, "winner_sha1": digest,
                              "overridden": shadowed})

        lower = rel.lower()
        if lower in case_index and case_index[lower] != rel:
            case_collisions.append((case_index[lower], rel))
        case_index[lower] = rel

        target = os.path.join(dest, rel.replace("/", os.sep))
        action = "copied"
        if os.path.isfile(target):
            try:
                if sha1_bytes(read_file(target)) == digest:
                    action = "unchanged"
                else:
                    action = "updated"
            except OSError:
                action = "updated"
        if action != "unchanged" and not args.dry_run:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as handle:
                handle.write(data)
            shutil.copystat(src, target)
        counts[action] += 1
        by_root[winner] += 1
        if not args.quiet and action != "unchanged":
            print("  %-9s %-6s %s" % (action, winner, rel))

        files[rel] = {
            "source_root": winner,
            "source_path": src,
            "sha1": digest,
            "bytes": len(data),
            "overridden_by": None,
            "overrides": [entry["root"] for entry in shadowed],
            "conflict": bool(shadowed),
        }
        for entry in shadowed:
            # Record, on the losing side, who overrode it.
            files[rel].setdefault("shadowed", []).append(entry)

    # Prune files this tool wrote that no longer exist in any root, and files
    # that an exclusion now withdraws.  Only when the file on disk still matches
    # bytes we can attribute to a previous collation - the manifest's sha1, or,
    # for an excluded path a manifest never recorded, the bytes the source root
    # still holds - so client rawfiles and hand edits are never destroyed.
    prune_records = dict(previous_files)
    for rel, pattern in excluded_paths.items():
        if rel in prune_records:
            continue
        source = None
        for name in reversed(ROOT_ORDER):
            if rel in scans[name]:
                source = scans[name][rel]
                break
        if not source:
            continue
        try:
            prune_records[rel] = {"sha1": sha1_bytes(read_file(source))}
        except OSError:
            continue
    pruned = []
    for rel, record in sorted(prune_records.items()):
        if rel in files:
            continue
        target = os.path.join(dest, rel.replace("/", os.sep))
        if not os.path.isfile(target):
            continue
        try:
            current = sha1_bytes(read_file(target))
        except OSError:
            continue
        if current != record.get("sha1"):
            warnings.append("stale %s differs from the last collation; left in place" % rel)
            continue
        if args.no_prune:
            warnings.append("stale %s is no longer in any root (--no-prune)" % rel)
            continue
        if not args.dry_run:
            os.remove(target)
            parent = os.path.dirname(target)
            while parent and os.path.isdir(parent) and parent != dest and not os.listdir(parent):
                os.rmdir(parent)
                parent = os.path.dirname(parent)
        pruned.append(rel)
        counts["pruned"] += 1
        print("  pruned    -      %s" % rel)

    manifest = {
        "tool": "tools/collate_gsc.py",
        "generated": datetime.datetime.now().replace(microsecond=0).isoformat(),
        "dest": dest,
        "roots": {name: roots[name] for name in ROOT_ORDER},
        "precedence_high_to_low": list(reversed(ROOT_ORDER)) + ["existing codol_rawfiles"],
        "loadable_extensions": list(LOADABLE_EXT),
        "loader": {
            "reader": "src/codol/script/codol_script_source.c "
                      "CODOL_ReadScriptSourceWithNativeOverlayForZone",
            "caller": "src/cscr_parser.cpp Scr_ReadFile",
            "probe_order": [
                "<native>/<zoneType>/<name>",
                "<native>/<name>",
                "<overlay>/<name>",
                "<base>/mp/<name>",
                "<base>/<name>",
            ],
        },
        "counts": dict(counts, total=len(files), by_root=by_root),
        "exclude_file": args.exclude_file,
        "exclusions": exclusions,
        "excluded_paths": dict(sorted(excluded_paths.items())),
        "conflicts": conflicts,
        "pruned": pruned,
        "warnings": warnings,
        "case_collisions": ["%s vs %s" % pair for pair in case_collisions],
        "files": files,
    }

    if not args.dry_run:
        os.makedirs(dest, exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest, handle, indent=1, sort_keys=False)
            handle.write("\n")

        lines = ["sh1x GSC collation conflicts",
                 "generated %s" % manifest["generated"],
                 "precedence (high to low): native(scripts/codol) > overlay(gsc_overlay) "
                 "> vendor(vendor/iw4) > existing codol_rawfiles",
                 "",
                 "%d of %d collated paths exist in more than one root." %
                 (len(conflicts), len(files)),
                 ""]
        for entry in conflicts:
            losers = ", ".join("%s%s" % (item["root"], " (identical)" if item["identical"] else "")
                               for item in entry["overridden"])
            lines.append("%-60s WON: %-7s  overrode: %s" % (entry["path"], entry["winner"], losers))
        if case_collisions:
            lines += ["", "Case collisions (Windows resolves these to one file):"]
            lines += ["  %s vs %s" % pair for pair in case_collisions]
        if warnings:
            lines += ["", "Warnings:"] + ["  " + w for w in warnings]
        with open(os.path.join(dest, CONFLICTS_NAME), "w", encoding="utf-8",
                  newline="\n") as handle:
            handle.write("\n".join(lines) + "\n")

    print()
    print("  total collated %d  (vendor %d, overlay %d, native %d)"
          % (len(files), by_root["vendor"], by_root["overlay"], by_root["native"]))
    print("  copied %d  updated %d  unchanged %d  pruned %d  failed %d  excluded %d"
          % (counts["copied"], counts["updated"], counts["unchanged"],
             counts["pruned"], counts["failed"], counts["excluded"]))
    print("  conflicts (path in >1 root): %d" % counts["conflicts"])
    for entry in conflicts:
        losers = ", ".join("%s%s" % (item["root"], " (identical)" if item["identical"] else "")
                           for item in entry["overridden"])
        print("    %-58s won:%-7s over %s" % (entry["path"], entry["winner"], losers))
    for warning in warnings:
        print("  warning: %s" % warning)
    for pair in case_collisions:
        print("  case collision: %s vs %s" % pair)
    if args.dry_run:
        print("  (dry run: nothing written)")
    else:
        print("  manifest  %s" % manifest_path)
        print("  conflicts %s" % os.path.join(dest, CONFLICTS_NAME))
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
