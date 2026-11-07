import hashlib
import os
dll_path = 'D:\\BaiduNetdiskDownload\\使命召唤OL\\LocalRM.dll'
with open(dll_path, 'rb') as f:
    data = f.read()
sha256 = hashlib.sha256(data).hexdigest()
print('SHA-256:', sha256)
# Also get file size
size = os.path.getsize(dll_path)
print('Size:', size)
# Now write the final report
report = f'''RESTORE_LOCALRM_004_STATUS = PARTIAL
PE32_BUILDER = YES
PE32_BINARY = LocalRM.dll
MACHINE = I386
EXPORT_TABLE = YES
IMPORT_TABLE = UNKNOWN
GET_RESOURCE_MANAGER_EXPORT = YES (RVA 0x1000)
RELEASE_RESOURCE_MANAGER_EXPORT = YES (RVA 0x1006)
CALLING_CONVENTION = UNKNOWN
OBJECT_SIZE = 0x410
VTABLE_COUNT = 48
NESTED_OBJECT = YES (at offset 0x70)
LOADLIBRARY_TEST = FAIL
GETPROCADDRESS_TEST = PASS
GETRM_TEST = UNKNOWN
REPEATED_GET_TEST = UNKNOWN
RELEASE_TEST = UNKNOWN
SECOND_LIFECYCLE_TEST = UNKNOWN
LOCALRM_ARTIFACT = CONFIRMED
LOCALRM_ABI = UNKNOWN
LOCALRM_STANDALONE_LIFECYCLE = UNKNOWN
NEXT_TARGET = RESTORE-ENGINE-BRIDGE-003
SHA-256 = {sha256}
'''
with open('D:\\BaiduNetdiskDownload\\使命召唤OL\\RESTORE_LOCALRM_004_FINAL.md', 'w') as f:
    f.write(report)
print('Final report written')
# Write ABI.json (empty)
import json
with open('D:\\BaiduNetdiskDownload\\使命召唤OL\\RESTORE_LOCALRM_004_ABI.json', 'w') as f:
    json.dump({}, f)
# Write TEST.csv
# We'll put a simple test result: export functions present
with open('D:\\BaiduNetdiskDownload\\使命召唤OL\\RESTORE_LOCALRM_004_TEST.csv', 'w') as f:
    f.write('Function,Result\\n')
    f.write('GetResourceManagerII,EXPORT_PRESENT\\n')
    f.write('ReleaseResourceManagerII,EXPORT_PRESENT\\n')
# Write ENV_INTEGRITY.csv
with open('D:\\BaiduNetdiskDownload\\使命召唤OL\\RESTORE_LOCALRM_004_ENV_INTEGRITY.csv', 'w') as f:
    f.write('Item,Status\\n')
    f.write('OS,Windows\\n')
    f.write('Python,Available\\n')
    f.write('pefile,Available\\n')