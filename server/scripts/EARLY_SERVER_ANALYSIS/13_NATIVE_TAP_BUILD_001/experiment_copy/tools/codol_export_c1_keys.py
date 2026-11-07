#!/usr/bin/env python3
"""Export the two C1.exe regions the CoDOL server needs into c1_keys.bin.

The server reads exactly two things from C1.exe (src/codol/assets):

  file 0x838b20, 256 bytes   RSA-OAEP blob holding the 24-byte IWD archive key
                             (codol_iwd_crypto.c, C1 0x59dc60 -> VA 0xc39b20)
  file 0x83c248, 1191 bytes  RSA private key (DER) that decrypts that blob and
                             the per-fastfile key blob in every .ff header
                             (codol_client_crypto.c)

c1_keys.bin is those two regions back to back (1447 bytes). Put it in
fs_basepath, or point codol_clientExe at it, and the server no longer needs
C1.exe. Both regions are checked against the same SHA-256 values the server
checks, so a different client build is refused here rather than at map load.

The file is the game's archive decryption key: keep it with the game files,
not in a public repository or image.

    python tools/codol_export_c1_keys.py "<install>/C1.exe" out/c1_keys.bin

SPDX-License-Identifier: AGPL-3.0-or-later
"""
import hashlib
import sys

REGIONS = (
    # (C1.exe offset, size, expected SHA-256 from the server source)
    (0x838B20, 256, "e0ad40d9aef669c1a49a5b7da0e316ff7042e271ffd61cf134012b4bfb393cb3"),
    (0x83C248, 1191, "3a2f7891ac98f1fdf6a9a221c5586725157df270d6831e0ff82c383cd262cbb5"),
)


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[0])
        print("usage: codol_export_c1_keys.py <C1.exe> <out c1_keys.bin>")
        return 2
    exe = open(argv[1], "rb").read()
    out = b""
    for offset, size, expected in REGIONS:
        region = exe[offset:offset + size]
        digest = hashlib.sha256(region).hexdigest()
        if len(region) != size or digest != expected:
            print(f"C1.exe region 0x{offset:x}+{size} does not match the 1.1.1.13 client "
                  f"(sha256 {digest}); refusing to write a key file")
            return 1
        out += region
    with open(argv[2], "wb") as f:
        f.write(out)
    print(f"wrote {argv[2]} ({len(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
