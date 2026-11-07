p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

# Replace the hardcoded b"\x00" * 32 with field648 read
old = '''        body_89 = (bytes([0x01, 1, 0x00]) + b"\\x00" * 32 +
                   struct.pack("<H", len(payload)) + payload +
                   struct.pack("<I", 0))'''

new = '''        # 32B session field must match [req+0x648] (memcmp at 0xBA1171)
        f648_path = self.echo_file.replace("echo.txt", "field648.txt")
        field648 = b"\\x00" * 32  # fallback
        try:
            f648_hex = open(f648_path, encoding="ascii").read().strip()
            if len(f648_hex) == 64:
                field648 = bytes.fromhex(f648_hex)
        except (OSError, ValueError):
            pass
        body_89 = (bytes([0x01, 1, 0x00]) + field648 +
                   struct.pack("<H", len(payload)) + payload +
                   struct.pack("<I", 0))'''

src = src.replace(old, new)
open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
