// SPDX-License-Identifier: MIT
// Desktop-only Arduino compatibility layer for documentation rendering.
#pragma once
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>
#include <type_traits>
#define PROGMEM
using std::min;
using std::max;
using std::abs;
using boolean = bool;
class __FlashStringHelper;
class String : public std::string {
public:
  using std::string::string;
  String(const std::string &value) : std::string(value) {}
  template<class T, typename std::enable_if<std::is_integral<T>::value,int>::type = 0>
  String(T value) : std::string(std::to_string(value)) {}
  String substring(size_t start, size_t end=std::string::npos) const {
    start=min(start,size()); end=min(end,size());
    return substr(start,end>start?end-start:0);
  }
  int lastIndexOf(char value, size_t from) const {
    auto pos=rfind(value,from); return pos==npos?-1:int(pos);
  }
  void trim() {
    while(!empty() && std::isspace(static_cast<unsigned char>(back()))) pop_back();
    while(!empty() && std::isspace(static_cast<unsigned char>(front()))) erase(begin());
  }
  void remove(size_t index) { if(index<size()) erase(index); }
};
inline String operator+(const String &left,int right) { return String(std::string(left)+std::to_string(right)); }
inline unsigned long millis() { return 0; }
inline void delay(unsigned long) {}
inline double radians(double degrees) { return degrees*3.14159265358979323846/180.0; }
