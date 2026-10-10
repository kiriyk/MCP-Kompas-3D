"""Minimal stdio-only MCP facade. No CAD work happens on protocol threads."""
import inspect
import asyncio
import logging
from mcp.server.fastmcp import FastMCP
from .adapter import Adapter, PUBLIC_TOOLS
from .worker import SerialWorker

def main():
    logging.basicConfig(level=logging.WARNING)
    server=FastMCP('kompas-local-v21')
    worker=SerialWorker(Adapter)
    def expose(name):
        method=getattr(Adapter,name)
        signature=inspect.signature(method)
        signature=signature.replace(parameters=[p for p in signature.parameters.values() if p.name!='self'])
        async def invoke(*args,**kwargs):
            bound=signature.bind(*args,**kwargs);bound.apply_defaults()
            return await asyncio.to_thread(worker.call,lambda adapter:getattr(adapter,name)(**bound.arguments))
        invoke.__name__=name;invoke.__doc__=method.__doc__;invoke.__signature__=signature
        invoke.__annotations__={k:v for k,v in method.__annotations__.items() if k!='self'}
        server.add_tool(invoke,name=name)
    for name in PUBLIC_TOOLS:expose(name)
    try:server.run(transport='stdio')
    finally:worker.close()

if __name__=='__main__':main()
