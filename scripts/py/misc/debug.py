import pefile
pe=pefile.PE('D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\IIPS\\iips.dll')
print(dir(pe.OPTIONAL_HEADER))