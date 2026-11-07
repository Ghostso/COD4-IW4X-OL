p="_dyn_game.py"
s=open(p,encoding="utf-8").read()
s=s.replace("PROCESS_QUERY_INFORMATION|PROCESS_VM_READ = 0x1F0FFF", "PROCESS_ALL_ACCESS = 0x1F0FFF")
open(p,"w",encoding="utf-8").write(s)
print("fixed")
