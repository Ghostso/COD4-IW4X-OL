import zlib, os

src_path = r"_e1_regression\ol-mod-olfinal\assets\backend\1004\Server\mp_playlists_shipRetail_release.info"
raw_text = open(src_path, "rb").read()
print(f"Plaintext size: {len(raw_text)} bytes")

# Check if version 796 is at the top
print("First 50 bytes:", raw_text[:50])

# Compress with zlib
compressed = zlib.compress(raw_text)
print(f"Zlib compressed size: {len(compressed)} bytes")

# Test roundtrip
decompressed = zlib.decompress(compressed)
assert decompressed == raw_text
print("Compression roundtrip verified!")
