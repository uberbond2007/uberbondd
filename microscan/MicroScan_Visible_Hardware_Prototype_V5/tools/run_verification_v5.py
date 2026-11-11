"""Run every V5 digital check and write an execution receipt with real exit codes and tool versions.

Nothing here touches hardware. Set MICROSCAN_PIO (and optionally PLATFORMIO_CORE_DIR) to include
the real ESP32 cross-compile; without it the build step is recorded as SKIPPED, never as passed.
"""
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
PIO = os.environ.get('MICROSCAN_PIO') or shutil.which('pio')
logs = []


def run(name, cmd, cwd=ROOT, timeout=1800, expect=0):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        code, out = p.returncode, (p.stdout + '\n' + p.stderr)
    except Exception as exc:  # recorded, not hidden
        code, out = 99, repr(exc)
    ok = (code == expect)
    logs.append({'name': name, 'command': ' '.join(str(c).replace(str(ROOT), '.').replace(PY, 'python') for c in cmd),
                 'exit_code': code, 'ok': ok, 'log_tail': out[-6000:]})
    print(('PASS' if ok else 'FAIL'), name, flush=True)
    return ok, out


def version(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[0]
    except Exception as exc:
        return f'unavailable ({exc.__class__.__name__})'


# 1. provenance
run('release_and_v4_integrity', [PY, '-m', 'unittest', '-v', 'checks.test_release_integrity_v5'])

# 2. reproduce the V4 release exactly as shipped, in a scratch copy
with tempfile.TemporaryDirectory() as td:
    work = Path(td) / 'v4'
    shutil.copytree(ROOT / 'source_v4' / 'extracted_unmodified', work)
    ok, out = run('v4_reproduction_run_verification', [PY, 'tools/run_verification.py'], cwd=work)
    receipt = work / 'reports' / 'V4_EXECUTION_RECEIPT.json'
    repro = {'reproduced_utc': datetime.now(timezone.utc).isoformat(), 'command': 'python tools/run_verification.py (unmodified V4 tree, scratch copy)',
             'exit_code': 0 if ok else 1, 'stdout': out.strip().splitlines()[-8:],
             'v4_receipt_regenerated': json.loads(receipt.read_text()) if receipt.is_file() else None,
             'note': 'REPRODUCED here; the receipt inside source_v4/ is the REPORTED original and is untouched.'}
    if repro['v4_receipt_regenerated']:
        for s in repro['v4_receipt_regenerated'].get('steps', []):
            s['log'] = s.get('log', '')[-800:]
    (ROOT / 'reports').mkdir(exist_ok=True)
    (ROOT / 'reports' / 'V4_REPRODUCTION_RECEIPT.json').write_text(json.dumps(repro, indent=2) + '\n')

# 3. mechanical
run('cad_build_v5', [PY, 'cad/build_hardware_v5.py'])
run('cad_validate_v5', [PY, 'checks/validate_cad_v5.py'])
run('audit_v2_against_hw818', [PY, 'checks/audit_v2_against_hw818.py'])
run('drawings_and_previews', [PY, 'drawings/generate_drawings_v5.py'])

# 4. host transport
run('host_transport_tests', [PY, '-m', 'unittest', 'discover', '-s', 'host/tests', '-v'])
with tempfile.TemporaryDirectory() as td:
    exe = Path(td) / 'packet_emitter'
    img = ROOT / 'source_v4' / 'extracted_unmodified' / 'reports' / 'SYNTHETIC_FRAME_ONLY.jpg'
    ok, _ = run('cpp_emitter_compile', ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', 'bench/packet_emitter.cpp', '-o', str(exe)])
    if ok:
        code = ("import subprocess,sys;sys.path.insert(0,'host');from microscan_usb_packet import decode_packet;"
                f"p=subprocess.run([r'{exe}',r'{img}','640','360'],capture_output=True);assert p.returncode==0;"
                f"m,j=decode_packet(p.stdout);assert j==open(r'{img}','rb').read();print(m)")
        run('cpp_emitter_to_python_parser', [PY, '-c', code])

# 5. firmware
run('firmware_source_checks', [PY, '-m', 'unittest', '-v', 'checks.test_firmware_source'])
run('firmware_interlock_on_mock', [PY, '-m', 'unittest', '-v', 'checks.test_firmware_interlock'])
if PIO:
    env_note = 'real ESP32 cross-compile executed'
    run('firmware_real_esp32_build', [PY, '-m', 'unittest', '-v', 'checks.test_firmware_build'])
else:
    env_note = 'SKIPPED: PlatformIO not found; firmware was NOT compiled in this run'
    logs.append({'name': 'firmware_real_esp32_build', 'command': 'python -m unittest checks.test_firmware_build', 'exit_code': None,
                 'ok': None, 'log_tail': env_note})
    print('SKIP firmware_real_esp32_build')

# 6. budgets and cost
run('optics_and_transfer_budget', [PY, 'checks/optics_and_transfer_budget.py'])
run('bom_arithmetic', [PY, '-m', 'unittest', '-v', 'checks.test_bom'])


def pyver(mod):
    try:
        return __import__(mod).__version__
    except Exception:
        return 'unavailable'


failed = [l['name'] for l in logs if l['ok'] is False]
skipped = [l['name'] for l in logs if l['ok'] is None]
report = {
    'utc': datetime.now(timezone.utc).isoformat(), 'phase': 'DIGITAL_ONLY',
    'physical_hardware_tested': False, 'printed': False, 'flashed': False, 'camera_image_captured': False,
    'esp32_firmware_compiled': bool(PIO) and 'firmware_real_esp32_build' not in failed,
    'esp32_firmware_compile_scope': 'capture-LOCKED bring-up image only; capture-capable image is refused by the gates',
    'firmware_build_note': env_note,
    'tools': {'python': platform.python_version(), 'platform': platform.platform(), 'cadquery': pyver('cadquery'),
              'trimesh': pyver('trimesh'), 'pillow': pyver('PIL'), 'numpy': pyver('numpy'), 'matplotlib': pyver('matplotlib'),
              'reportlab': pyver('reportlab'), 'g++': version(['g++', '--version']),
              'platformio': version([PIO, '--version']) if PIO else 'not installed'},
    'steps': logs, 'passed': sum(1 for l in logs if l['ok']), 'failed': len(failed), 'skipped': len(skipped),
    'failed_steps': failed, 'skipped_steps': skipped}
(ROOT / 'reports' / 'V5_EXECUTION_RECEIPT.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS_STEPS', report['passed'], 'FAIL_STEPS', report['failed'], 'SKIPPED', report['skipped'])
raise SystemExit(1 if failed else 0)
