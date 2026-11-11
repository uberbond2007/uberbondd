import io, sys, unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from microscan_usb_packet import build_packet, decode_packet, FrameError
class PacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        im=Image.new('RGB',(85,47),(245,245,245))
        b=io.BytesIO(); im.save(b,format='JPEG',quality=92)
        cls.jpg=b.getvalue(); cls.packet=build_packet(cls.jpg,85,47)
    def test_valid(self):
        meta,jpg=decode_packet(self.packet)
        self.assertEqual(meta['width'],85); self.assertEqual(meta['height'],47)
        self.assertEqual(jpg,self.jpg)
    def test_serial_prefix(self):
        meta,jpg=decode_packet(b'BOOT READY\n'+self.packet+b'\nFINISH')
        self.assertEqual(jpg,self.jpg)
    def test_absent_magic(self):
        with self.assertRaisesRegex(FrameError,'No MSJ1'):decode_packet(self.jpg)
    def test_truncated_header(self):
        with self.assertRaisesRegex(FrameError,'header'):decode_packet(b'MSJ1')
    def test_truncated_body(self):
        with self.assertRaisesRegex(FrameError,'Truncated JPEG'):decode_packet(self.packet[:-18])
    def test_bad_crc(self):
        mutated=bytearray(self.packet); mutated[-3]^=1
        with self.assertRaisesRegex(FrameError,'CRC32'):decode_packet(bytes(mutated))
    def test_bad_dimensions(self):
        mutated=bytearray(self.packet); mutated[8]=3
        with self.assertRaisesRegex(FrameError,'dimensions'):decode_packet(bytes(mutated))
    def test_invalid_count(self):
        mutated=bytearray(self.packet); mutated[4:8]=(99999999).to_bytes(4,'little')
        with self.assertRaisesRegex(FrameError,'Impossible JPEG length'):decode_packet(bytes(mutated))
    def test_jpeg_marker_does_not_suffice(self):
        # Valid CRC over invalid JPEG markers should still fail image decoding.
        bogus=b'\xff\xd8not a valid JPEG\xff\xd9'
        with self.assertRaises(FrameError): decode_packet(build_packet(bogus,85,47))
    def test_header_mismatch(self):
        mutated=bytearray(self.packet); mutated[8:10]=(100).to_bytes(2,'little')
        with self.assertRaisesRegex(FrameError,'dimensions'):decode_packet(bytes(mutated))
if __name__=='__main__':unittest.main()
