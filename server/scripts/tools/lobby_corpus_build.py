#!/usr/bin/env python3
"""把历次 run 的 lobby_tasks.bin 汇总成字节级语料。

lobby_tasks.bin 记录格式 (lobby_server.py:1447):
    u8 service | u8 task | u32le len | payload[len]
连续拼接，无文件头。

产物: corpus.json (每条记录带来源 run)、corpus_stats.txt
只读输入，不改任何 run 目录。
"""
import json
import os
import struct
import sys
from collections import defaultdict


def read_records(path):
    with open(path, "rb") as f:
        b = f.read()
    off, out = 0, []
    while off + 6 <= len(b):
        svc = b[off]
        task = b[off + 1]
        n = struct.unpack_from("<I", b, off + 2)[0]
        if off + 6 + n > len(b):
            out.append({"svc": svc, "task": task, "len": n,
                        "payload": b[off + 6:].hex(), "truncated": True})
            break
        out.append({"svc": svc, "task": task, "len": n,
                    "payload": b[off + 6:off + 6 + n].hex()})
        off += 6 + n
    return out, len(b) - off


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "run_codol_001/runs"
    outdir = sys.argv[2] if len(sys.argv) > 2 else "."
    os.makedirs(outdir, exist_ok=True)

    files = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn == "lobby_tasks.bin":
                p = os.path.join(dirpath, fn)
                files.append((os.path.getmtime(p), p))
    files.sort()

    corpus = []
    bad = []
    for mtime, p in files:
        run = os.path.basename(os.path.dirname(os.path.dirname(p)))
        recs, tail = read_records(p)
        if tail:
            bad.append((run, tail))
        for i, r in enumerate(recs):
            r["run"] = run
            r["idx"] = i
            corpus.append(r)

    with open(os.path.join(outdir, "corpus.json"), "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False)

    # 统计
    per_pair = defaultdict(list)
    for r in corpus:
        per_pair[(r["svc"], r["task"])].append(r)

    lines = []
    lines.append("files=%d records=%d pairs=%d" % (len(files), len(corpus), len(per_pair)))
    if bad:
        lines.append("TRUNCATED_TAIL: %r" % (bad,))
    lines.append("")
    lines.append("%-4s %-5s %-6s %-6s %-8s %s" % ("svc", "task", "count", "minlen", "maxlen", "distinct_payload"))
    for (svc, task) in sorted(per_pair):
        rs = per_pair[(svc, task)]
        lens = [r["len"] for r in rs]
        distinct = len({r["payload"] for r in rs})
        lines.append("%-4d %-5d %-6d %-6d %-8d %d" % (
            svc, task, len(rs), min(lens), max(lens), distinct))

    with open(os.path.join(outdir, "corpus_stats.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines[:3]))


if __name__ == "__main__":
    main()
