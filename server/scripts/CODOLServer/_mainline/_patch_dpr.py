import re,io
p="_dyn_pop_run.py"
s=open(p,encoding="utf-8").read()
s=s.replace('ROOT = sys.argv[1]\nOUT  = sys.argv[2]\nSECS = float(sys.argv[3]) if len(sys.argv) > 3 else 95.0',
 'HERE = os.path.dirname(os.path.abspath(__file__))\nROOT = os.path.abspath(os.path.join(HERE, "..", ".."))\nOUT  = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "_dyn_pop_out")\nSECS = float(sys.argv[2]) if len(sys.argv) > 2 else 95.0')
open(p,"w",encoding="utf-8").write(s)
print("patched")
