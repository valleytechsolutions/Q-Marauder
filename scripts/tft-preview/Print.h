// SPDX-License-Identifier: MIT
#pragma once
#include "Arduino.h"
class Print {
public:
  virtual ~Print() = default;
  virtual size_t write(uint8_t value) = 0;
  size_t print(const String &value) {
    size_t count=0; for(unsigned char c:value) count+=write(c); return count;
  }
  size_t print(const char *value) { return print(String(value)); }
};
