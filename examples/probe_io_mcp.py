"""Protocol verification after the direct native IO probe."""
import json
from pathlib import Path
from client import Client

def run():
 out=Path(__file__).resolve().parents[1]/'artifacts';docs=[]
 with Client() as c:
  try:
   c.call('connect');s=c.call('create_drawing')['document_id'];docs.append(s)
   c.call('set_sheet',document_id=s,format='A1',landscape=True)
   c.call('create_view',document_id=s,name='Source',scale=.1,x=50,y=60)
   rectangle=c.call('rectangle',document_id=s,x=1000,y=2000,width=1200,height=800)
   c.call('text',document_id=s,x=500,y=3500,value='MCP: — → × Ø',height=8)
   c.call('arc',document_id=s,x=4000,y=3000,radius=500,start_angle=0,end_angle=90)
   assert c.call('get_selected_objects',document_id=s)['items']==[]
   t=c.call('create_drawing')['document_id'];docs.append(t)
   c.call('create_view',document_id=t,name='Target',scale=.02,x=100,y=200)
   result=c.call('copy_objects_to_document',source_id=s,target_id=t,references=[rectangle['reference']],dx=200,dy=300)
   assert result['copied']==1 and result['items'][0]['base']==[1200,2300]
   c.call('save_document',document_id=s,path=str(out/'io-mcp.cdw'))
   for paper in ('sheet','A4'):
    for color in (True,False):c.call('export_pdf',document_id=s,path=str(out/f'io-mcp-{paper}-{color}.pdf'),paper=paper,color=color)
   assert c.call('document_state',document_id=s)['sheet']['format']=='A1'
   print('IO MCP PASS',len(c.records),'calls',flush=True)
  finally:
   for d in reversed(docs):c.call('close_document',document_id=d)
   (out/'io-mcp-results.json').write_text(json.dumps(c.records,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':run()
