import os

root = os.path.join("COD OL", "IIPS")
for base, dirs, files in os.walk(root):
    for name in files:
        if name.lower().endswith((".dll", ".exe", ".ini", ".tprj", ".xml")):
            path = os.path.join(base, name)
            print("%9d  %s" % (os.path.getsize(path), path))
