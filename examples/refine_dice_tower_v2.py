"""V2 refinement now uses the public staged MCP builder."""
from build_dice_tower_v2 import build
import argparse
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--executable');a=p.parse_args();print(build(a.output,a.executable))
