import os 
files=os.listdir('_dyn_stage1') 
print([x for x in files if x.startswith('_tcls')][:30]) 
