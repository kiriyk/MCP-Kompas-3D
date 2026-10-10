import subprocess, threading, queue, json, time, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

base = Path(r'C:\Users\user\Documents\Codex\kompas-mcp\v1.0.22\KOMPAS-3D-MCP-bin')
p = subprocess.Popen([str(base / 'kompas-mcp.exe')], cwd=base,
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
out = queue.Queue()
def read_output():
    for line in p.stdout:
        try: out.put(json.loads(line))
        except ValueError: pass
threading.Thread(target=read_output, daemon=True).start()
def read_errors():
    for line in p.stderr: pass
threading.Thread(target=read_errors, daemon=True).start()
def request(n, method, params, timeout=25):
    p.stdin.write(json.dumps({'jsonrpc':'2.0','id':n,'method':method,'params':params})+'\n'); p.stdin.flush()
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        try: reply=out.get(timeout=max(.1,end-time.monotonic()))
        except queue.Empty: break
        if reply.get('id')==n: return reply
    return {'error':'timeout','method':method}
try:
    r=request(1,'initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'Codex connection check','version':'1.0'}})
    print(json.dumps({'initialize':r},ensure_ascii=False),flush=True)
    if 'result' in r:
        p.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'})+'\n'); p.stdin.flush()
        actions = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')) if len(sys.argv)>1 else [{'name':'get_active_document','arguments':{'compact':True}},{'name':'snapshot_state','arguments':{'compact':True,'detail_level':'summary'}}]
        for index, action in enumerate(actions,2):
            reply=request(index, 'tools/call', action, timeout=40)
            for block in reply.get('result',{}).get('content',[]):
                if block.get('type')=='image': block['data']='[image saved by MCP; omitted from log]'
            print(json.dumps({'tool':action['name'],'reply':reply},ensure_ascii=False),flush=True)
            if 'error' in reply or reply.get('result',{}).get('isError'): break
finally:
    p.terminate()
