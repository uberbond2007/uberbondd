"""Runs offline validation and saves actual subprocess receipts. Requires Python + g++."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
steps=[
    ('serial_transport_tests',[sys.executable,'-m','unittest','discover','-s','host/tests','-v']),
    ('release_checks',[sys.executable,'-m','unittest','discover','-s','checks','-p','test_release_integrity.py','-v']),
    ('cad_geometry',[sys.executable,'checks/validate_cad.py']),
    ('cad_meshes',[sys.executable,'checks/validate_exported_meshes.py']),
]
logs=[]
for name,command in steps:
    try:
        p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120)
        code=p.returncode; out=p.stdout+'\n'+p.stderr
    except Exception as exc:
        code=99;out=str(exc)
    logs.append({'name':name,'command':command,'exit_code':code,'log':out[-15000:]})
    print(name, 'PASS' if code==0 else 'FAIL')
# Cross language integrity test, using the C++ reference CRC32 implementation from the firmware.
with tempfile.TemporaryDirectory() as td:
    exe=Path(td)/'packet_emitter'; packet=Path(td)/'packet.bin'
    img=ROOT/'reports'/'SYNTHETIC_FRAME_ONLY.jpg'
    w,h=Image.open(img).size
    cp=subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',str(ROOT/'bench'/'packet_emitter.cpp'),'-o',str(exe)],capture_output=True,text=True)
    status=99;details=''
    if cp.returncode==0:
        with packet.open('wb') as dst:
            run=subprocess.run([str(exe),str(img),str(w),str(h)],stdout=dst,stderr=subprocess.PIPE)
        if run.returncode==0:
            sys.path.insert(0,str(ROOT/'host'))
            from microscan_usb_packet import decode_packet
            try:
                meta,jpeg=decode_packet(packet.read_bytes())
                assert jpeg==img.read_bytes()
                status=0;details=f'C++ CRC32 encoder -> Python strict JPEG decoder passed; width={w}, height={h}, bytes={len(jpeg)}'
            except Exception as exc:
                details=f'FAILED: {exc}'
        else: details=f'Emitter exit {run.returncode}'
    else: details='Compiler error: '+cp.stderr[-3000:]
    logs.append({'name':'cpp_to_python_protocol','command':'g++ -std=c++17 ... && packet_emitter JPG W H && Python decode_packet','exit_code':status,'log':details})
    print('cpp_to_python_protocol', 'PASS' if status==0 else 'FAIL',details)
report={'utc':datetime.now(timezone.utc).isoformat(),'phase':'DIGITAL_ONLY',
        'physical_hardware_tested':False,'esp32_arduino_firmware_compiled':False,
        'steps':logs,'passed':sum(l['exit_code']==0 for l in logs),'failed':sum(l['exit_code']!=0 for l in logs)}
(ROOT/'reports'/'V4_EXECUTION_RECEIPT.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS_STEPS', report['passed'],'FAIL_STEPS',report['failed'])
raise SystemExit(bool(report['failed']))
