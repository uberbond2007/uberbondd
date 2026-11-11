import os
import pty
import sys
import tempfile
import threading
import time
import unittest
from io import BytesIO
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from microscan_usb_packet import build_packet, decode_packet
from serial_capture import capture, read_one_packet, CaptureError

class SerialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        im=Image.new('RGB',(64,48),'white')
        b=BytesIO(); im.save(b,format='JPEG')
        cls.image=b.getvalue(); cls.packet=build_packet(cls.image,64,48)
    def simulated_capture(self, packet=None, prefix=b'boot message\r\n', split=53, timeout=1.0):
        master, slave=pty.openpty()
        dev=os.ttyname(slave)
        output=tempfile.TemporaryDirectory()
        def virtual_device():
            os.read(master,128)  # waits for explicit CAPTURE\n command
            data=prefix+(packet or self.packet)
            try:
                for i in range(0,len(data),split):
                    os.write(master,data[i:i+split]); time.sleep(.0001)
            except OSError: pass
        t=threading.Thread(target=virtual_device,daemon=True); t.start()
        try:
            result=capture(dev,Path(output.name)/'out.jpg',timeout)
            self.assertEqual((result['width'],result['height']),(64,48))
            self.assertEqual(Path(output.name,'out.jpg').read_bytes(),self.image)
        finally:
            t.join(timeout=.4); os.close(master); os.close(slave); output.cleanup()
    def test_one_shot_real_posix_pty(self): self.simulated_capture()
    def test_fragmented_one_byte_at_time(self): self.simulated_capture(split=1)
    def test_false_magic_before_frame(self): self.simulated_capture(prefix=b'MSJ1'+b'broken nonsense boot\n')
    def test_false_magic_single_chunk(self): self.simulated_capture(prefix=b"MSJ1"+b"broken nonsense boot\n",split=100000)
    def test_crc_error_not_written(self):
        p=bytearray(self.packet); p[-10]^=1
        master,slave=pty.openpty(); dev=os.ttyname(slave)
        def send():
            os.read(master,128); os.write(master,p)
        th=threading.Thread(target=send,daemon=True); th.start()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(CaptureError):capture(dev,Path(d)/'a.jpg',2)
            self.assertFalse(Path(d,'a.jpg').exists())
        th.join(timeout=.4);os.close(master);os.close(slave)
    def test_timeout(self):
        master,slave=pty.openpty(); dev=os.ttyname(slave)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(CaptureError):capture(dev,Path(d)/'a.jpg',.05)
        os.close(master);os.close(slave)
    def test_malformed_header(self):
        p=b'MSJ1'+b'\xff'*12
        master,slave=pty.openpty()
        os.write(master,p)
        with self.assertRaises(CaptureError):read_one_packet(slave, .1)
        os.close(master);os.close(slave)

if __name__=='__main__':unittest.main()
