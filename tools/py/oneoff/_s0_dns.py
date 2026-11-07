import subprocess, re
out=subprocess.run(["ipconfig","/displaydns"],capture_output=True).stdout.decode("gbk","replace")
entries=[]
name=None
for line in out.splitlines():
    m=re.search(r"Record Name\s*\.+\s*:\s*(\S+)", line)
    if m:
        name=m.group(1); continue
    m=re.search(r"A \(Host\) Record\s*\.+\s*:\s*(\d+\.\d+\.\d+\.\d+)", line)
    if m and name:
        entries.append((name,m.group(1)))
seen=set()
for n,ip in entries:
    if (n,ip) in seen: continue
    seen.add((n,ip))
    print("%-32s %s"%(n,ip))
