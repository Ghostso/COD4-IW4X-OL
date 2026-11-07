import pefile,struct  
p=pefile.PE('COD OL/codoMP_client_shipRetail.exe')  
img=p.get_memory_mapped_image()  
needle=struct.pack('<I',0xddbf80)  
start=0  
while True:  
    i=img.find(needle,start)  
    if i<0: break  
    print(hex(i))  
    start=i+1  
