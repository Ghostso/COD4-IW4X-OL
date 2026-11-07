
import ctypes, os, sys
try:
    admin = ctypes.windll.shell32.IsUserAnAdmin()
except Exception as e:
    admin = "err:%s" % e
print("IsUserAnAdmin:", admin)
print("user:", os.environ.get("USERNAME"), "domain:", os.environ.get("USERDOMAIN"))
print("elevated:", os.environ.get("__COMPAT_LAYER"))
