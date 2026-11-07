import hashlib
cands = {
 "http://127.0.0.1:8080/": None,
 "http://127.0.0.1/": None,
 "http://10.231.2.181/": None,
 "iips#policy!@#$%": None,
}
for s in cands:
    b=s.encode()
    print("%-28s md5hex=%s  md5hex_lower_input=%s" % (s, hashlib.md5(b).hexdigest(), hashlib.md5(b.lower()).hexdigest()))
