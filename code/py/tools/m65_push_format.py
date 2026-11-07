#!/usr/bin/env python3
"""§七 #7: 6/5 事件推送格式 —— 从客户端找它的解码器.
   先在镜像搜 6/5 相关字符串/log 关键字, 再找 'ReadQueuedMessages' 之类.
   已知: 6/5 = ReadQueuedMessages(offset/maxResults/consume). 推送格式 = 服务端推回来的东西.
   搜: 'ReadQueuedMessages', 'QueuedMessages', 'queuePush', 'msgType' 等.
"""
import re
E=r"E:\codol_re\client_image_20261027.bin"
d=open(E,"rb").read(); N=len(d)
words=["ReadQueuedMessages","QueuedMessage","queued_message","queuePush","QueuePush",
       "populateQueue","PushMessage","messageQueue","eventPush","EventPush",
       "subscribe","Subscribe","channelData","ChannelData"]
print("=== 关键字命中 ===")
for w in words:
    pat=w.encode()
    hits=[];i=0
    while True:
        p=d.find(pat,i)
        if p<0: break
        hits.append(p);i=p+1
        if len(hits)>=6: break
    print("  %-20s %s"%(w,["0x%X"%h for h in hits] or "—"))
