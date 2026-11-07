p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()

old = """        calc = hmac8(hmac_out, fr["raw"][:-8])
        ok = (calc == fr["tag"])
        try:
            plain = aes128cbc_dec(aes_out, fr["iv"], fr["cipher"])
        except Exception as e:
            self.log("!! decrypt error: %s" % e)
            return"""

new = """        calc = hmac8(hmac_out, fr["raw"][:-8])
        ok = (calc == fr["tag"])
        if not ok:
            # The client may have just reconnected with fresh keys.  The
            # observer writes secrets at 2 Hz, so wait briefly and retry.
            for _ in range(10):
                time.sleep(0.2)
                self.secrets.load()
                aes_out2 = self.secrets.get("aes_out")
                hmac_out2, _ = self.secrets.hmac_keys()
                if aes_out2 and hmac_out2:
                    calc2 = hmac8(hmac_out2, fr["raw"][:-8])
                    if calc2 == fr["tag"]:
                        ok = True
                        aes_out = aes_out2
                        hmac_out = hmac_out2
                        self.log("   hmac retry OK after secrets refresh")
                        break
        try:
            plain = aes128cbc_dec(aes_out, fr["iv"], fr["cipher"])
        except Exception as e:
            self.log("!! decrypt error: %s" % e)
            return"""

src = src.replace(old, new)
open(p, "w", encoding="utf-8", newline="").write(src)
print("patched")
