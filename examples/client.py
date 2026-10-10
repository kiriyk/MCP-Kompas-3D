"""Small standard JSON-RPC stdio client for reproducible local examples."""
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

class Client:
    def __init__(self,timeout=60):
        self.timeout=timeout;self.sequence=0;self.queue=queue.Queue();self.records=[]
        self.process=subprocess.Popen([sys.executable,'-m','kompas_local_mcp.server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.stderr=[]
        threading.Thread(target=self._read,daemon=True).start()
        threading.Thread(target=self._errors,daemon=True).start()
        self.request('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'kompas-local-mcp-test','version':'0.1'}})
        self.process.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'})+'\n');self.process.stdin.flush()
    def _read(self):
        for line in self.process.stdout:
            try:self.queue.put(json.loads(line))
            except ValueError:self.queue.put({'error':{'message':'Non-JSON stdout: '+line[:100]}})
        self.queue.put({'error':{'message':'Server exited'}})
    def _errors(self):
        for line in self.process.stderr:self.stderr.append(line)
    def request(self,method,params):
        self.sequence+=1
        self.process.stdin.write(json.dumps({'jsonrpc':'2.0','id':self.sequence,'method':method,'params':params},ensure_ascii=False)+'\n');self.process.stdin.flush()
        while True:
            reply=self.queue.get(timeout=self.timeout)
            if reply.get('id')==self.sequence or ('error' in reply and 'id' not in reply):
                if 'error' in reply:raise RuntimeError(str(reply)+'\n'+''.join(self.stderr)[-4000:])
                return reply['result']
    def call(self,tool_name,**arguments):
        reply=self.request('tools/call',{'name':tool_name,'arguments':arguments})
        value=reply.get('structuredContent')
        if value is None:
            for item in reply.get('content',[]):
                if item.get('type')=='text':
                    try:value=json.loads(item['text'])
                    except ValueError:value=item['text']
                    break
        self.records.append({'tool':tool_name,'arguments':arguments,'isError':reply.get('isError',False),'result':value})
        if reply.get('isError'):raise RuntimeError(f'{tool_name}: {value}')
        return value
    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=5)
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
