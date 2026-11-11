"""Decode a SINGLE operator-requested MSJ1 camera frame from a USB-serial log.
This is an OFFLINE parser. It does not trigger cameras or open network ports.
"""
import argparse, io, json, struct, sys, zlib
from pathlib import Path
from PIL import Image, UnidentifiedImageError

MAGIC=b'MSJ1'
HEADER=struct.Struct('<4sIHHI')
MAX_FRAME_BYTES=10_000_000

class FrameError(ValueError):
    pass

def decode_packet(stream: bytes):
    idx=stream.find(MAGIC)
    if idx < 0: raise FrameError('No MSJ1 JPEG packet in supplied serial bytes')
    if len(stream)-idx<HEADER.size: raise FrameError('Truncated MSJ1 header')
    magic, count, width, height, crc=HEADER.unpack_from(stream,idx)
    if not (2<=count<=MAX_FRAME_BYTES): raise FrameError('Impossible JPEG length')
    if not (1<=width<=5000 and 1<=height<=5000): raise FrameError('Invalid dimensions')
    start=idx+HEADER.size
    payload=stream[start:start+count]
    if len(payload)!=count: raise FrameError('Truncated JPEG payload')
    if (zlib.crc32(payload)&0xffffffff)!=crc: raise FrameError('CRC32 mismatch')
    if payload[:2]!=b'\xff\xd8' or payload[-2:]!=b'\xff\xd9':
        raise FrameError('Payload is not a complete JPEG stream')
    try:
        with Image.open(io.BytesIO(payload)) as im:
            im.load()
            if im.format!='JPEG': raise FrameError('Payload not JPEG')
            if im.size!=(width,height): raise FrameError('Camera header/image dimensions disagree')
    except (UnidentifiedImageError,OSError) as e: raise FrameError('Image decoding failed') from e
    return {'width':width,'height':height,'bytes':count,'crc32':f'{crc:08x}'}, payload

def build_packet(image_bytes:bytes, width:int, height:int)->bytes:
    if len(image_bytes)>MAX_FRAME_BYTES: raise FrameError('Too large')
    return HEADER.pack(MAGIC,len(image_bytes),width,height,zlib.crc32(image_bytes)&0xffffffff)+image_bytes

def main():
    ap=argparse.ArgumentParser(description='Decode one frame from a captured serial byte log')
    ap.add_argument('serial_bytes_file',type=Path)
    ap.add_argument('--jpeg',type=Path,required=True)
    args=ap.parse_args()
    metadata,jpeg=decode_packet(args.serial_bytes_file.read_bytes())
    args.jpeg.parent.mkdir(parents=True,exist_ok=True)
    args.jpeg.write_bytes(jpeg)
    print(json.dumps({'jpeg':str(args.jpeg),**metadata},indent=2))
if __name__=='__main__':
    try: main()
    except FrameError as exc:
        print(f'FAILED: {exc}',file=sys.stderr)
        sys.exit(2)
