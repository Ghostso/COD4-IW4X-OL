import re
p=r"CODOLServer\_mainline\watch_connects.py"
s=open(p,encoding="utf-8").read()
print(s[s.find("def main"):])
