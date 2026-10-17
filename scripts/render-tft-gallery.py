"""Render real sketch drawing functions to PNG, without a board or radio jobs.

Requires a C++17 compiler and a separate Adafruit GFX Library 1.12.6 checkout.
No upstream library is bundled. The Arduino/parallel-bus shims are documentation
tools only; resulting images are software renders, not physical TFT photographs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib


def png(raw):
    header=b'P6\n320 480\n255\n'
    if not raw.startswith(header) or len(raw)!=len(header)+320*480*3:
        raise ValueError('Unexpected canvas dimensions')
    pixels=raw[len(header):]
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    scanlines=b''.join(b'\0'+pixels[y*960:(y+1)*960] for y in range(480))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',320,480,8,2,0,0,0))
            +chunk(b'IDAT',zlib.compress(scanlines,9))+chunk(b'IEND',b''))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gfx',type=Path,required=True,help='Separately installed Adafruit GFX 1.12.6 directory')
    parser.add_argument('--compiler',default='g++')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    output=args.output or root/'docs/images/tft'
    gfx=args.gfx.resolve()
    if 'version=1.12.6' not in (gfx/'library.properties').read_text():
        raise SystemExit('Use the same Adafruit GFX version as flash-display.sh: 1.12.6')
    source=root/'firmware/uno_shield/uno_shield.ino'
    original=source.read_text()
    # Compile the current sketch's complete drawing section without its RPC/GPIO loop.
    drawing=original.split('void openMenu(int target)',1)[0]
    if 'void render()' not in drawing: raise SystemExit('Sketch layout changed; review renderer extraction')
    drawing=drawing.replace('#include <Arduino_RouterBridge.h>','')
    drawing=drawing.replace('#include "Parallel9486.h"','#include "Panel.h"')
    drawing=drawing.replace('#include "TouchControls.h"','')
    scenes={'bwm-boot':(0,-1,0),'bwm-home':(0,0,0),'marauder-detection':(1,13,0),
            'biscuit-settings':(2,12,0),'valleytech-ble':(3,15,0),'theme-picker':(0,14,0),
            'linux-tools':(3,18,0),'linux-analysis':(1,18,1),'linux-history-menu':(0,18,2)}
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='qm-tft-gallery-') as scratch:
        temporary=Path(scratch)
        main_cpp=drawing+'''
int main(int argc,char **argv) {
  if(argc!=5) return 2;
  theme=std::atoi(argv[1]); menu=std::atoi(argv[2]); page=std::atoi(argv[3]);
  orientation=0; touch.calibrated=true; connected=false;
  if(menu<0) { bootScreen(); animateBoot(); } else render();
  lcd.save(argv[4]);
}
'''
        cpp=temporary/'preview.cpp';cpp.write_text(main_cpp)
        binary=temporary/'preview'
        subprocess.run([args.compiler,'-std=c++17','-DARDUINO=10800',
            '-I',str(root/'scripts/tft-preview'),'-I',str(root/'firmware/uno_shield'),'-I',str(gfx),
            str(cpp),str(gfx/'Adafruit_GFX.cpp'),'-o',str(binary)],check=True)
        for name,(theme,menu,page) in scenes.items():
            ppm=temporary/(name+'.ppm')
            subprocess.run([str(binary),str(theme),str(menu),str(page),str(ppm)],check=True)
            (output/(name+'.png')).write_bytes(png(ppm.read_bytes()))
    manifest=dict(kind='software-render',resolution=[320,480],observations='none; zero counters; bridge disconnected',
        source='firmware/uno_shield/uno_shield.ino',
        source_sha256=hashlib.sha256(original.replace('\r\n','\n').encode()).hexdigest(),
        gfx_version='1.12.6',scenes=scenes)
    (output/'provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Rendered',len(scenes),'firmware scenes to',output)


if __name__=='__main__': main()
