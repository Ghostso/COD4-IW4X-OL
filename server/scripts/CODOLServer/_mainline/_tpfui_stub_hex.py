import os

path = r"COD OL\IIPS\TPFUI\IIPSRes\back\SystemSetting\button.png"
blob = open(path, "rb").read()
print("size=%d" % len(blob))
print(blob.hex(" "))
print(repr(blob))
