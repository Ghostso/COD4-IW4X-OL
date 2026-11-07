import re
p = r"CODOLServer\lobby3074\lsg_server.py"
src = open(p, encoding="utf-8").read()
# Replace the 71/4 block: find "if key == (71, 4):" through "return [" before next "if"
pat = r'(        if key == \(71, 4\):\n)(.*?)(\n        if key in self\.handlers:)'
repl = ('        if key == (71, 4):\n'
        '            self.log("     71/4  -> empty (upload/ack)")\n'
        '            return []\n'
        '\n')
src2 = re.sub(pat, repl, src, count=1, flags=re.S)
open(p, "w", encoding="utf-8", newline="").write(src2)
print("done")
