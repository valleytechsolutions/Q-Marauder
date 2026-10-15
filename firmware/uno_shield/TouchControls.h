// SPDX-License-Identifier: MIT
// Standard four-wire resistive shield. MCU drives every excitation at 3.3 V.
// X/Y/pressure measurement follows Adafruit TouchScreen's published circuit method.
#pragma once
#include <Arduino.h>
#include <stm32u5xx_ll_gpio.h>
struct TouchSample { int x, y, pressure; bool down; };
class TouchControls {
  static constexpr uint8_t XP=6, XM=A2, YP=A1, YM=7;
  void floating(uint8_t pin) { pinMode(pin, INPUT); }
  void drive(uint8_t pin, bool high) { pinMode(pin, OUTPUT); digitalWrite(pin, high ? HIGH : LOW); }
  int read(uint8_t pin) {
    // Factory zephyr 0.11 analogRead configures the ADC but does not restore
    // analog pad mode after pinMode(INPUT/OUTPUT) on shared touch/LCD pins.
    // UNO Q A1=PA5 and A2=PA6, as defined by its board device tree.
    LL_GPIO_SetPinMode(GPIOA, pin==A1?LL_GPIO_PIN_5:LL_GPIO_PIN_6, LL_GPIO_MODE_ANALOG);
    delayMicroseconds(60); analogRead(pin); return analogRead(pin);
  }
public:
  int axis=1, top=0, bottom=0;
  bool calibrated=false;
  TouchSample sample() {
    digitalWrite(A3, HIGH); digitalWrite(A0, HIGH); // LCD deselected, no read
    floating(YP); floating(YM); drive(XP,true); drive(XM,false);
    int x=read(YP), x2=read(YP);
    floating(XP); floating(XM); drive(YP,true); drive(YM,false);
    int y=read(XM), y2=read(XM);
    floating(XM); floating(YP); drive(XP,false); drive(YM,true);
    int z1=read(XM), z2=read(YP), pressure=1023-(z2-z1);
    return {x,y,pressure, pressure>100 && pressure<1000 && abs(x-x2)<18 && abs(y-y2)<18};
  }
  bool set(int a,int t,int b) {
    if ((a!=0 && a!=1) || t<0 || t>1023 || b<0 || b>1023 || abs(t-b)<250) return false;
    axis=a; top=t; bottom=b; calibrated=true; return true;
  }
  int screenY(const TouchSample &p) {
    return constrain(36 + long((axis?p.y:p.x)-top)*408/(bottom-top),0L,479L);
  }
};
