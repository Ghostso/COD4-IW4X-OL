p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()
# Remove the mtime cache check: always reload
old = """            if st.st_mtime == self.mtime and self.data:
                return True"""
new = """            # Always reload: the observer writes continuously (2 Hz) and the
            # client re-derives keys on every reconnect.  A stale cache here
            # causes HMAC verification failures on the second connection."""
src = src.replace(old, new)
open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
