// SPDX-License-Identifier: MIT
// Standard MCUFRIEND UNO shield bus. No AVR-specific port writes.
#pragma once
#include <Arduino.h>
#include <Adafruit_GFX.h>

class Parallel9486 : public Adafruit_GFX {
  const uint8_t dataPins[8] = {8, 9, 2, 3, 4, 5, 6, 7};
  static constexpr uint8_t RD = A0, WR = A1, DC = A2, CS = A3, RST = A4;
  uint8_t reflections = 0;
  void bus(uint8_t value) {
    for (uint8_t i = 0; i < 8; ++i) digitalWrite(dataPins[i], (value >> i) & 1);
  }
  void strobe() { digitalWrite(WR, LOW); digitalWrite(WR, HIGH); }
  void byte(uint8_t value) { bus(value); strobe(); }
  void command(uint8_t value) {
    digitalWrite(DC, LOW); byte(value); digitalWrite(DC, HIGH);
  }
  void reg(uint8_t cmd, const uint8_t *values, uint8_t size) {
    digitalWrite(CS, LOW); command(cmd);
    for (uint8_t i = 0; i < size; ++i) byte(values[i]);
    digitalWrite(CS, HIGH);
  }
  void reg1(uint8_t cmd, uint8_t value) { reg(cmd, &value, 1); }
  void window(int16_t x, int16_t y, int16_t w, int16_t h) {
    uint16_t right = x + w - 1, bottom = y + h - 1;
    uint8_t cols[] = {uint8_t(x >> 8), uint8_t(x), uint8_t(right >> 8), uint8_t(right)};
    uint8_t rows[] = {uint8_t(y >> 8), uint8_t(y), uint8_t(bottom >> 8), uint8_t(bottom)};
    reg(0x2A, cols, 4); reg(0x2B, rows, 4);
    digitalWrite(CS, LOW); command(0x2C);
  }
public:
  uint16_t readId = 0;
  uint16_t profile = 0x9486;
  Parallel9486() : Adafruit_GFX(320, 480) {}
  uint32_t readRegister(uint8_t cmd) {
    digitalWrite(CS, LOW); command(cmd);
    for (uint8_t pin : dataPins) pinMode(pin, INPUT);
    uint32_t result = 0;
    for (uint8_t b = 0; b < 4; ++b) {
      digitalWrite(RD, LOW); delayMicroseconds(5);
      uint8_t value = 0;
      for (uint8_t i = 0; i < 8; ++i) value |= uint8_t(digitalRead(dataPins[i]) != LOW) << i;
      result = (result << 8) | value;
      digitalWrite(RD, HIGH); delayMicroseconds(5);
    }
    digitalWrite(CS, HIGH);
    for (uint8_t pin : dataPins) pinMode(pin, OUTPUT);
    return result;
  }
  void begin() {
    // A0/A1 are driven at the UNO Q's own 3.3 V. Only tolerant D2-D9
    // become inputs for the controller ID read. Touch initializes separately.
    for (uint8_t pin : {RD, WR, DC, CS, RST}) { pinMode(pin, OUTPUT); digitalWrite(pin, HIGH); }
    pinMode(10, OUTPUT); digitalWrite(10, HIGH); // deselect shield SD
    for (uint8_t pin : dataPins) pinMode(pin, OUTPUT);
    delay(50); digitalWrite(RST, LOW); delay(100); digitalWrite(RST, HIGH); delay(150);
    readId = uint16_t(readRegister(0xD3));
    if (readId == 0x9488) profile = 0x9488;
    // Unknown/write-only reads retain the explicitly selected 9486 profile.
    reg(0x01, nullptr, 0); delay(150);
    // Panel parameters adapted from MCUFRIEND_kbv; see licenses/MCUFRIEND.txt.
    if (profile == 0x9486) {
      const uint8_t power[] = {0x0D, 0x0D}, power2[] = {0x43, 0};
      const uint8_t vcom[] = {0, 0x48, 0, 0x48}, function[] = {2, 2, 0x3B};
      const uint8_t gammaP[] = {15,33,28,11,14,8,73,152,56,9,17,3,20,16,0};
      const uint8_t gammaN[] = {15,47,43,12,14,6,71,118,55,7,17,4,35,30,0};
      reg(0xC0, power, 2); reg(0xC1, power2, 2); reg1(0xC2, 0);
      reg(0xC5, vcom, 4); reg1(0xB4, 0); reg(0xB6, function, 3);
      reg(0xE0, gammaP, 15); reg(0xE1, gammaN, 15);
    } else {
      const uint8_t power[] = {0x10, 0x10}, vcom[] = {0, 0x22, 0x80, 0x40};
      const uint8_t function[] = {2, 2, 0x3B}, adjust[] = {0xA9, 0x51, 0x2C, 0x82};
      reg(0xC0, power, 2); reg1(0xC1, 0x41); reg(0xC5, vcom, 4);
      reg1(0xB4, 2); reg(0xB6, function, 3); reg(0xF7, adjust, 4);
    }
    reg1(0x3A, 0x55); // 16-bit RGB565 on 8-bit parallel bus
    reg1(0x36, 0x08); // Fixed portrait address mode; reflection is applied in software.
    reg(0x20, nullptr, 0); reg(0x11, nullptr, 0); delay(150);
    reg(0x29, nullptr, 0); delay(50);
  }
  void portraitAxes(uint8_t value) {
    // Keep the panel's address mode fixed. Some shields reporting 0x9486
    // accept MADCTL MX/MY writes without correcting the visible image.
    // Every primitive uses solid rectangles, so reflecting their coordinates
    // also reflects individual glyph pixels and the decoded logo runs.
    reflections = value & 3;
  }
  void restoreBus() {
    digitalWrite(CS, HIGH);
    for (uint8_t pin : dataPins) pinMode(pin, OUTPUT);
    for (uint8_t pin : {RD, WR, DC, CS}) { pinMode(pin, OUTPUT); digitalWrite(pin, HIGH); }
  }
  void drawPixel(int16_t x, int16_t y, uint16_t color) override { fillRect(x, y, 1, 1, color); }
  void drawFastHLine(int16_t x, int16_t y, int16_t w, uint16_t color) override { fillRect(x,y,w,1,color); }
  void drawFastVLine(int16_t x, int16_t y, int16_t h, uint16_t color) override { fillRect(x,y,1,h,color); }
  void fillRect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color) override {
    if (x < 0) { w += x; x = 0; } if (y < 0) { h += y; y = 0; }
    if (x + w > width()) w = width() - x;
    if (y + h > height()) h = height() - y;
    if (w <= 0 || h <= 0) return;
    if (reflections & 1) x = width() - x - w;
    if (reflections & 2) y = height() - y - h;
    window(x, y, w, h);
    uint32_t count = uint32_t(w) * h;
    uint8_t hi = color >> 8, lo = color;
    if (hi == lo) {
      bus(hi); while (count--) { strobe(); strobe(); }
    } else {
      while (count--) { byte(hi); byte(lo); }
    }
    digitalWrite(CS, HIGH);
  }
};
