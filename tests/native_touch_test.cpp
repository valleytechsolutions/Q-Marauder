// Compile with g++ -std=c++17 -I firmware/uno_shield tests/native_touch_test.cpp
#include <cassert>
#include <iostream>
#include "TouchGeometry.h"
#include "DisplayLayout.h"
int main() {
  TouchGeometry t;
  assert(t.screenX(500,500)==-1);
  assert(t.set(150,180,850,180,150,880));
  assert(t.screenX(150,180)==36 && t.screenY(150,180)==56);
  assert(t.screenX(850,180)==284 && t.screenY(850,180)==56);
  assert(t.screenX(150,880)==36 && t.screenY(150,880)==424);
  assert(t.screenX(500,530)==160 && t.screenY(500,530)==240);
  assert(t.set(850,880,150,880,850,180));
  assert(t.screenX(500,530)==160 && t.screenY(500,530)==240);
  assert(t.screenX(150,880)==284 && t.screenY(850,180)==424);
  assert(t.set(180,150,180,850,880,150));
  assert(t.screenX(530,500)==160 && t.screenY(530,500)==240);
  assert(t.screenX(180,850)==284 && t.screenY(880,150)==424);
  assert(!t.set(0,0,500,500,1000,1000));
  assert(!t.set(0,0,1024,0,0,900));
  assert(!t.set(0,0,10,0,0,10));
  assert(Layout::hit(50,130,7,0)==10);
  assert(Layout::hit(50,200,7,0)==11);
  assert(Layout::hit(50,280,7,0)==12);
  assert(Layout::hit(50,350,7,0)==13);
  assert(Layout::hit(50,184,7,0)==-1); // Gap cannot select the adjacent row.
  assert(Layout::hit(5,130,7,0)==-1);
  assert(Layout::hit(50,350,7,1)==-1); // No fourth item on page 2.
  assert(Layout::hit(50,450,7,0)==0);
  assert(Layout::hit(160,450,7,0)==-1); // Previous disabled on page 1.
  assert(Layout::hit(260,450,7,0)==2);
  assert(Layout::hit(160,450,7,1)==1);
  assert(Layout::hit(260,450,7,1)==-1);
  assert(Layout::hit(50,130,7,0,true)==-1); // Details only have Back.
  assert(Layout::hit(260,450,7,0,true)==-1);
  assert(Layout::hit(50,450,7,0,true)==0);
  std::cout << "Touch geometry and direct-hit navigation checks passed\n";
}
