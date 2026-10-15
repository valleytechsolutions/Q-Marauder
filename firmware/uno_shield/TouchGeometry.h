// SPDX-License-Identifier: MIT
#pragma once
#include <stdint.h>

// Three measured targets define an affine map, including swapped/inverted axes.
// Targets: (36,56), (284,56), (36,424) in the final portrait orientation.
struct TouchGeometry {
  int raw[6]={};
  bool calibrated=false;
  int64_t determinant=0;
  bool set(int x0,int y0,int x1,int y1,int x2,int y2) {
    const int candidate[]={x0,y0,x1,y1,x2,y2};
    for(int v:candidate) if(v<0 || v>1023) return false;
    int64_t det=int64_t(x1-x0)*(y2-y0)-int64_t(y1-y0)*(x2-x0);
    if(det>-60000 && det<60000) return false;
    for(int i=0;i<6;++i) raw[i]=candidate[i];
    determinant=det; calibrated=true; return true;
  }
  int screenX(int x,int y) const {
    int64_t u=int64_t(x-raw[0])*(raw[5]-raw[1])-int64_t(y-raw[1])*(raw[4]-raw[0]);
    return calibrated?36+int(u*248/determinant):-1;
  }
  int screenY(int x,int y) const {
    int64_t v=int64_t(raw[2]-raw[0])*(y-raw[1])-int64_t(raw[3]-raw[1])*(x-raw[0]);
    return calibrated?56+int(v*368/determinant):-1;
  }
};
