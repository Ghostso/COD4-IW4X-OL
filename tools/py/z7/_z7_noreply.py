p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()
# 71/4: don't reply at all
old = """        if key == (71, 4):
            self.log("     71/4  -> empty (upload/ack)")
            return []"""
new = """        if key == (71, 4):
            self.log("     71/4  -> NO REPLY (fire-and-forget)")
            return None  # caller checks for None and skips the reply"""
src = src.replace(old, new)

# In decrypt_and_reply, skip reply if handle_task returns None
old2 = """        objs = self.handle_task(inner)
        rid = self.reply_id"""
new2 = """        objs = self.handle_task(inner)
        if objs is None:
            self.log("   no reply sent (handler returned None)")
            return
        rid = self.reply_id"""
src = src.replace(old2, new2)

open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
