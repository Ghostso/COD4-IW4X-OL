p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()
old = '''        if key == (71, 4):
            self.log("     71/4  -> NO REPLY (fire-and-forget)")
            return None  # caller checks for None and skips the reply'''
new = '''        if key == (71, 4):
            self.log("     71/4  -> identity objects")
            return [
                obj_file(b"\\x00" * 16),
                obj_file(USER_NAME.encode("ascii")),
                obj_file(_pattern(0x80, 0x20)),
                obj_file(b"\\x00" * 0x80),
            ]'''
src = src.replace(old, new)
open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
