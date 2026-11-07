"""Extract the embedded IWff fastfiles from an IIPS ".ifs" container.

Container layout (reverse-engineered, see HANDOFF section 50.8/50.10):

    offset 0x00  'nifs'                       magic
    offset 0x04  u32 header_len (=0xAC)       header size
    offset 0x08  u32[n]                       end-offset table
    ...          ASCII name list
    offset 0xAC  32-byte signature/hash
    offset 0xB8  name list continues, then the payload
    payload      one or more 'IWff0100' fastfile blobs, contiguous

This tool only READS the .ifs and WRITES extracted .ff files to an output
directory.  It never modifies the source container.

Usage:
  python -X utf8 CODOLServer/_mainline/_ifs_extract.py <in.ifs> <outdir>
"""
from __future__ import annotations

import os
import re
import struct
import sys

MAGIC = b"nifs"
FF_MAGIC = b"IWff"


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src, outdir = sys.argv[1], sys.argv[2]
    blob = open(src, "rb").read()
    if blob[:4] != MAGIC:
        print("not a nifs container:", blob[:4])
        return 1
    hlen = struct.unpack_from("<I", blob, 4)[0]
    print("container %s (%d bytes), header_len=0x%X"
          % (os.path.basename(src), len(blob), hlen))

    # Collect the ASCII name list that lives between the offset table and the
    # payload.  Names we care about end in '.ff'.
    names = []
    for m in re.finditer(rb"[ -~]{4,120}", blob[:0x2000]):
        t = m.group(0)
        if t.endswith(b".ff") or t.endswith(b".lst"):
            names.append((m.start(), t.decode("ascii")))
    for off, nm in names:
        print("  name @0x%04X  %s" % (off, nm))

    # Locate all fastfile blobs.
    starts = [m.start() for m in re.finditer(re.escape(FF_MAGIC), blob)]
    print("IIWff blobs:", len(starts), [hex(s) for s in starts])

    ff_names = [n for _, n in names if n.endswith(".ff")]
    os.makedirs(outdir, exist_ok=True)
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(blob)
        if i < len(ff_names):
            base = os.path.basename(ff_names[i])
        else:
            base = "blob%d.ff" % i
        dst = os.path.join(outdir, base)
        with open(dst, "wb") as fh:
            fh.write(blob[start:end])
        print("  wrote %-46s %10d bytes (magic %s)"
              % (base, end - start, blob[start:start + 10].hex()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
