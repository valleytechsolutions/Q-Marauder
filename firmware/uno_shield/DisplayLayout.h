// SPDX-License-Identifier: MIT
#pragma once
namespace Layout {
constexpr int rowTop=116, rowHeight=64, rowStride=72, pageSize=4;
constexpr int footerTop=420, footerHeight=56;
constexpr int keyTop=172,keyStride=48,keyHeight=44,keySlots=20,keyChars=19;
inline int keyHit(int x,int y) {
  if(x<10 || x>=310 || y<keyTop || y>=keyTop+5*keyStride) return -1;
  int col=(x-10)/76,row=(y-keyTop)/keyStride;
  if(col>=4 || (x-10)%76>=72 || (y-keyTop)%keyStride>=keyHeight) return -1;
  return row*4+col;
}
// 0=Back/Themes, 1=Previous, 2=Next, 10..13=direct row. Gaps are inert.
inline int hit(int x,int y,int count,int page,bool detail=false) {
  if(y>=footerTop && y<footerTop+footerHeight) {
    if(x>=10 && x<106) return 0;
    if(!detail && x>=112 && x<208 && page>0) return 1;
    if(!detail && x>=214 && x<310 && (page+1)*pageSize<count) return 2;
  }
  if(detail || x<10 || x>=310 || y<rowTop) return -1;
  int row=(y-rowTop)/rowStride;
  if(row<pageSize && (y-rowTop)%rowStride<rowHeight && page*pageSize+row<count) return 10+row;
  return -1;
}
}
