import ssl, socket, sys
for ip in ["101.72.248.61","116.131.60.72","81.71.56.93"]:
    try:
        ctx=ssl._create_unverified_context()
        s=socket.create_connection((ip,443),timeout=6)
        ss=ctx.wrap_socket(s,server_hostname=None)
        c=ss.getpeercert()
        print(ip,"->",c.get("subject"),"| issuer:",(c.get("issuer") or [()])[0])
        ss.close()
    except Exception as e:
        print(ip,"ERR",type(e).__name__,e)
