import socket
for ip in ['218.12.125.26','121.29.3.147','101.72.248.61']:
 try:
  print(ip,socket.gethostbyaddr(ip))
 except Exception as e: print(ip,type(e).__name__,e)
