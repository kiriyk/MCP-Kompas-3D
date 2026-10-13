"""Portable staged example runs: never overwrite a previously published native model."""
import hashlib,json,uuid
from pathlib import Path

class RunStore:
    def __init__(self,output):
        self.root=Path(output).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self.runs=self.root/'runs';self.runs.mkdir(exist_ok=True)
        self.current=self.root/'current.json'

    def begin(self):
        run=self.runs/('run-'+uuid.uuid4().hex[:12]);run.mkdir();return run

    def reusable(self,fingerprint):
        if not self.current.is_file():return None
        data=json.loads(self.current.read_text(encoding='utf-8'))
        if data.get('fingerprint')!=fingerprint:return None
        run=(self.root/data['run']).resolve()
        if not run.is_relative_to(self.runs):raise ValueError('Manifest path escapes run directory')
        for relative,digest in data['files'].items():
            p=(run/relative).resolve()
            if not p.is_relative_to(run):raise ValueError('Manifest file path escapes run directory')
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:return None
        return run

    def publish(self,run,fingerprint,verification):
        run=Path(run).resolve()
        if not run.is_relative_to(self.runs) or not verification.get('native_verified'):raise ValueError('Only a verified run inside this output root can be published')
        files={str(p.relative_to(run)):hashlib.sha256(p.read_bytes()).hexdigest() for p in run.rglob('*') if p.is_file() and p.suffix.lower() in ('.m3d','.a3d','.cdw','.pdf','.png')}
        if not files:raise ValueError('No deliverables to publish')
        data={'run':str(run.relative_to(self.root)),'fingerprint':fingerprint,'files':files,'verification':verification}
        stage=self.current.with_suffix('.tmp');stage.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');stage.replace(self.current)
        return data
