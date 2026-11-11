"""Write MANIFEST.json (SHA-256 of every file) and a deterministic ZIP beside the release folder."""
from hashlib import sha256
from pathlib import Path
import json
import zipfile

root = Path(__file__).resolve().parents[1]
out = root.parent / (root.name + '.zip')
manifest_path = root / 'MANIFEST.json'
SKIP_DIRS = {'__pycache__', '.pio', '.pytest_cache'}
files = sorted(p for p in root.rglob('*') if p.is_file() and p != manifest_path
               and not (set(p.parts) & SKIP_DIRS) and p.suffix != '.pyc')
manifest = {
    'project': 'MicroScan Visible Hardware V5',
    'scope': 'Digital fabrication package; firmware compiled as capture-locked bring-up image only; '
             'NOT printed, NOT assembled, NOT flashed, no image captured',
    'predecessor': {'file': 'source_v4/MicroScan_Visible_Hardware_Prototype_V4.zip',
                    'sha256': sha256((root / 'source_v4' / 'MicroScan_Visible_Hardware_Prototype_V4.zip').read_bytes()).hexdigest()},
    'file_count': len(files),
    'entries': {p.relative_to(root).as_posix(): {'sha256': sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size} for p in files},
}
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in sorted(files + [manifest_path]):
        info = zipfile.ZipInfo(f'{root.name}/{p.relative_to(root).as_posix()}', date_time=(2026, 11, 11, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for name, meta in manifest['entries'].items():
        assert sha256(z.read(f'{root.name}/{name}')).hexdigest() == meta['sha256'], name
    assert len(z.namelist()) == len(files) + 1
digest = sha256(out.read_bytes()).hexdigest()
(out.with_suffix('.zip.sha256')).write_text(f'{digest}  {out.name}\n')
print('FILE', out.name, 'MEMBERS', len(files) + 1, 'SIZE', out.stat().st_size, 'SHA256', digest)
