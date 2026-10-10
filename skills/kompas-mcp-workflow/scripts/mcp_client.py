"""Use the project's stdio Client in one session; default is tools/list only."""
import argparse
import importlib.util
import json
import os
import queue
import time
from pathlib import Path
import re
import subprocess
import sys

def resolve(value,bindings):
    if isinstance(value,str):
        match=re.fullmatch(r'\$\{([A-Za-z_]\w*)\}',value)
        if match:
            if match[1] not in bindings:raise ValueError(f'Unbound variable: {match[1]}')
            return bindings[match[1]]
    if isinstance(value,list):return [resolve(v,bindings) for v in value]
    if isinstance(value,dict):return {k:resolve(v,bindings) for k,v in value.items()}
    return value

def call_guarded(client,name,arguments,pause=time.sleep):
    try:
        return client.call(name,**arguments)
    except (RuntimeError,queue.Empty) as original:
        uncertain=isinstance(original,queue.Empty) or any(s in str(original).lower() for s in ('timed out','outcome unknown','worker busy'))
        if uncertain:
            print('Outcome unknown; batch stopped. Waiting for worker using read-only connect; no mutation retry.',file=sys.stderr,flush=True)
            while True:
                pause(5)
                try:
                    client.call('connect')
                    print('Worker responds again. Inspect document/object state in a new session before continuing.',file=sys.stderr,flush=True)
                    break
                except (RuntimeError,queue.Empty) as pending:
                    if isinstance(pending,queue.Empty) or any(s in str(pending).lower() for s in ('timed out','outcome unknown','worker busy')):
                        print('Still waiting for COM worker.',file=sys.stderr,flush=True)
                        continue
                    raise RuntimeError(f'Recovery probe failed; outcome remains unknown: {pending}') from original
        raise

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',default=r'C:\Users\user\DevProjects\MCP-Kompas-3D')
    parser.add_argument('--actions',help='Reviewed UTF-8 JSON array of tool calls')
    parser.add_argument('--schemas',action='store_true',help='Print full discovery schemas')
    args=parser.parse_args();project=Path(args.project).resolve();python=project/'.venv/Scripts/python.exe'
    if not python.is_file():raise ValueError(f'Project Python not found: {python}')
    if Path(sys.executable).resolve()!=python.resolve():
        child=subprocess.run([str(python),str(Path(__file__).resolve()),*sys.argv[1:]],check=False,capture_output=True,text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        sys.stdout.reconfigure(encoding='utf-8',errors='replace')
        print(child.stdout,end='',flush=True);print(child.stderr,end='',file=sys.stderr,flush=True)
        return child.returncode
    os.environ.setdefault('KOMPAS_EXECUTABLE',r'D:\ASCON\KOMPAS-3D v21\Bin\KOMPAS.exe')
    os.environ.setdefault('KOMPAS_MCP_CACHE',str(project/'.kompas-cache'))
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    client_file=project/'examples/client.py'
    spec=importlib.util.spec_from_file_location('kompas_project_client',client_file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    actions=[] if not args.actions else json.loads(Path(args.actions).read_text(encoding='utf-8-sig'))
    if not isinstance(actions,list):raise ValueError('Actions must be a JSON array')
    with module.Client(timeout=75) as client:
        discovery=client.request('tools/list',{});names={t['name'] for t in discovery['tools']}
        print(json.dumps(discovery if args.schemas else {'tools':sorted(names),'count':len(names)},ensure_ascii=False),flush=True)
        # Reject a legacy/unknown tool anywhere in a batch before its first mutation.
        for action in actions:
            if not isinstance(action,dict) or action.get('name') not in names:raise ValueError('Unknown action/tool')
            if not isinstance(action.get('arguments',{}),dict) or not isinstance(action.get('bind',{}),dict):raise ValueError('arguments/bind must be objects')
            for alias,key in action.get('bind',{}).items():
                if not re.fullmatch(r'[A-Za-z_]\w*',alias) or not isinstance(key,str):raise ValueError('Invalid binding name/field')
        bindings={}
        for action in actions:
            result=call_guarded(client,action['name'],resolve(action.get('arguments',{}),bindings))
            print(json.dumps({'tool':action['name'],'result':result},ensure_ascii=False),flush=True)
            if isinstance(result,dict) and result.get('success') is False:raise RuntimeError('Tool reported success=false')
            for alias,key in action.get('bind',{}).items():
                if not re.fullmatch(r'[A-Za-z_]\w*',alias):raise ValueError('Invalid binding name')
                if not isinstance(result,dict) or key not in result:raise ValueError(f'Missing result field: {key}')
                bindings[alias]=result[key]
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as error:
        print(f'{type(error).__name__}: {error}',file=sys.stderr);sys.exit(1)
