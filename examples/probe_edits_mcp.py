"""Verify the native edits through the stdio tools after direct API probe."""
import json
from pathlib import Path
from client import Client

def run():
 out=Path(__file__).resolve().parents[1]/'artifacts';d=None
 with Client() as c:
  try:
   c.call('connect');d=c.call('create_drawing')['document_id']
   def call(tool_name,**args):return c.call(tool_name,document_id=d,**args)
   call('create_view',name='Edit MCP',scale=.02,x=100,y=200)
   r=call('rectangle',x=0,y=0,width=5000,height=4000)
   t=call('text',x=1000,y=2000,value='До правки',height=4)
   call('move_objects',references=[r['reference'],t['reference']],dx=3000,dy=2000)
   call('resize_rectangle',reference=r['reference'],width=6000,height=4000)
   call('edit_text',reference=t['reference'],value='После правки — 6 × 4 м')
   objects=call('list_objects')['items']
   assert next(o for o in objects if o['api_reference']==r['api_reference'])['base']==[3000,2000]
   assert next(o for o in objects if o['api_reference']==r['api_reference'])['width']==6000
   assert next(o for o in objects if o['api_reference']==t['api_reference'])['value']=='После правки — 6 × 4 м'
   call('save_document',path=str(out/'edit-mcp.cdw'))
   call('export_png',path=str(out/'edit-mcp.png'),color_mode='layer',dpi=100)
   print('MCP EDIT PASS',len(c.records),'calls',flush=True)
  finally:
   if d:c.call('close_document',document_id=d)
   (out/'edit-mcp-results.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':run()
