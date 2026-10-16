// SPDX-License-Identifier: MIT
#pragma once
#include <Adafruit_GFX.h>
#include <fstream>
#include <stdexcept>
class Parallel9486 : public GFXcanvas16 {
public:
  Parallel9486() : GFXcanvas16(320,480) { setTextWrap(false); }
  void portraitAxes(int) {} // Preview logical upright coordinates, not panel wiring.
  uint32_t readRegister(int) { return 0; }
  void save(const char *path) {
    std::ofstream out(path,std::ios::binary);
    if(!out) throw std::runtime_error("Cannot write preview");
    out << "P6\n320 480\n255\n";
    for(int i=0;i<320*480;i++) {
      auto c=getBuffer()[i];
      const char rgb[]={char((c>>11)*255/31),char(((c>>5)&63)*255/63),char((c&31)*255/31)};
      out.write(rgb,3);
    }
  }
};
struct TouchControls { bool calibrated=true; };
struct TouchSample { int x,y,z; bool valid; };
