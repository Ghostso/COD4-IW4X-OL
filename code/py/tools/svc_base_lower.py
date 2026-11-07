#!/usr/bin/env python3
"""Base.dll 里搜小写服务名与 102 邻近。"""
import struct
PATH = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
data = open(PATH, "rb").read()
N=len(data)
names=[b"leaderboard",b"matchmaking",b"marketplace",b"presence",b"messaging",
       b"publisher_storage",b"publisherstorage",b"storage",b"eventlog",b"stats",
       b"friends",b"task",b"reward",b"clan",b"party",b"room",b"lobby",b"session"]
def findall(b):
    out=[];i=0
    while True:
        p=data.find(b,i)
        if p<0:return out
        out.append(p);i=p+1
for nm in names:
    hs=findall(nm)
    print("%-20s n=%d %s"%(nm.decode(),len(hs),["0x%X"%h for h in hs[:6]]))
