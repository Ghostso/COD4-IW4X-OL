# OLFinal fastfile repacking

`tools/reverse/OlfinalFastfile.py` converts an already serialized, inflated
OLFinal `.zone` body into the native encrypted `.ff` container. It implements
the format recovered from `out.exe` build 1649370:

- `IWff0100`, version 461 outer header;
- RSA-2048 PKCS#1 v1.5 wrapping of a per-file AES-192 key and IV;
- little-endian AES CTR with a reset for every 0x2000-byte block;
- the block-zero signed header, zone-name binding, level-one and level-two
  SHA-256 tables;
- zlib level-1 compression.

The Tencent signing private key is not present in the game. The tool borrows a
structurally valid signature from any shipped OLFinal fastfile. Run the matching
plugin with `OLMOD_ALLOW_UNSIGNED_FASTFILES=1`; its build-pinned patch accepts
the RSA verdict at `out.exe` `0x0048371A`. Native header, version, name, hash,
decryption and inflate checks still run. The switch is off by default and is
installed in both client and dedicated processes at the plugin's earliest entry.

```powershell
py -3 tools\reverse\OlfinalFastfile.py `
  C:\path\my_zone.zone C:\path\my_zone.ff `
  --exe C:\Games\OLfinal\out.exe `
  --template C:\Games\OLfinal\client_shipretail\chinese\aa12_mp.ff
```

The output name supplies the zone-name binding unless `--name` is given. The
tool decrypts and validates the template signature, writes through a temporary
file, and decrypts/inflates its own output before replacing the destination.
It requires PyCryptodome. `OlfinalFastfileTests.py` covers deterministic
multi-block round trips and corruption rejection.

This is a container writer, not an asset compiler. A `.zone` body must already
obey OLFinal's 16-byte `XAsset` table, eight stream blocks and pointer-fixup
rules before it can load.
