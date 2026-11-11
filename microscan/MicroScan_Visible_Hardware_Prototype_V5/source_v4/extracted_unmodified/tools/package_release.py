"""Deterministic archive of V4 with per-file SHA-256. Run after validation."""
from pathlib import Path
from hashlib import sha256
import json
import zipfile

root=Path(__file__).resolve().parents[1]
out=root.parent/(root.name+'.zip')
manifest_path=root/'RELEASE_MANIFEST.json'
files=sorted(p for p in root.rglob('*') if p.is_file() and p!=manifest_path and '__pycache__' not in p.parts and p.suffix!='.pyc')
manifest={'project':'MicroScan Visible Hardware V4','scope':'Digital preflight; no physical assembly','entries':{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in files}}
manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
all_files=sorted(files+[manifest_path])
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in all_files:
        name=f'{root.name}/{p.relative_to(root)}'
        info=zipfile.ZipInfo(name,date_time=(2026,11,10,0,0,0))
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o100644<<16
        z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for name,digest in manifest['entries'].items():
        assert sha256(z.read(f'{root.name}/{name}')).hexdigest()==digest
print('FILE',out,'MEMBERS',len(all_files),'SIZE',out.stat().st_size,'SHA256',sha256(out.read_bytes()).hexdigest())
