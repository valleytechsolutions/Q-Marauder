// SPDX-License-Identifier: MIT
#include <Arduino_RouterBridge.h>
#include "Parallel9486.h"
#include "TouchControls.h"
#include "DisplayLayout.h"
#include "LogoData.h"
#include "MenuData.h"
#include <Fonts/FreeSans9pt7b.h>

Parallel9486 lcd;
TouchControls touch;
struct Palette { const char *name; uint16_t bg,panel,accent,text,muted,watermark; };
const Palette themes[]={
  {"BWM",0x0841,0x10A3,0xF926,0xEF7D,0xA514,0x2803},
  {"Marauder",0x0862,0x1905,0xC638,0xEF7D,0x9CD3,0x3003},
  {"Cyber",0x0062,0x0905,0x2EDF,0xEF7D,0x94D3,0x0947}
};
constexpr uint16_t GREEN=0x47E9, RED=0xF926;
int theme=0;
bool themeChosen=false;
String headline="Waiting for Linux", infoTitle="", infoText="";
int wifiCount=0,bleCount=0,sessionCount=0,menu=0,page=0,themeReturnMenu=0;
int pendingAction=0,actionSequence=0,calibrationStep=0;
int calibrationRaw[6]={};
bool hasGps=false,connected=false,dirty=true,statusDirty=true;
unsigned long lastUpdate=0,lastSample=0,releaseAt=0;
int stable=0,pressX=0,pressY=0,pressedHit=-1;
bool held=false,releasePending=false;
uint32_t renderMs=0;
TouchSample lastTouch={0,0,0,false};
const uint8_t orientations[]={1,3,0,2};
int orientation=-1,orientationIndex=0;
unsigned long orientationSince=0;
uint32_t orientationReadback=0;
bool splashPending=false,calibrationRestoreAllowed=false;

void textStyle(uint8_t size) {
  lcd.setFont(size==2?&FreeSans9pt7b:nullptr);
  lcd.setTextSize(size==2?1:size);
}
void label(int x,int y,const String &value,uint16_t color,uint8_t size=2) {
  textStyle(size); lcd.setCursor(x,y+(size==2?14:0)); lcd.setTextColor(color); lcd.print(value);
}
void centered(int x,int y,int width,const String &value,uint16_t color,int size=2) {
  textStyle(size); int16_t left,top; uint16_t w,h;
  lcd.getTextBounds(value,0,0,&left,&top,&w,&h);
  label(x+(width-int(w))/2-left,y,value,color,size);
}
void wrapped(int x,int y,String value,uint16_t color,int columns=23,int maxLines=2) {
  for(int line=0;line<maxLines && value.length();++line) {
    int n=min(int(value.length()),columns);
    if(int(value.length())>columns) { int space=value.lastIndexOf(' ',columns); if(space>columns/2) n=space; }
    label(x,y+line*20,value.substring(0,n),color);
    value=value.substring(n); value.trim();
  }
}
void logo(int x,int y,int width,const uint16_t *runs,size_t count) {
  uint32_t position=0;
  for(size_t i=0;i<count;++i) {
    uint16_t remaining=runs[i*2];
    while(remaining) {
      uint16_t col=position%width,n=min(int(remaining),width-col);
      lcd.fillRect(x+col*2,y+(position/width)*2,n*2,2,runs[i*2+1]);
      remaining-=n; position+=n;
    }
  }
}
void watermark() {
  // Render the supplied red emblem as a faint silhouette, behind the text.
  // Runtime tinting preserves the original artwork and needs no framebuffer.
  uint32_t position=0;
  for(size_t i=0;i<sizeof(bwmRuns)/sizeof(bwmRuns[0]);++i) {
    int remaining=bwmRuns[i][0]; uint16_t color=bwmRuns[i][1];
    bool ink=((color>>11)&31)>8 && ((color>>11)&31)>int((color>>5)&63)/2+3;
    while(remaining) {
      int col=position%bwmWidth,n=min(remaining,int(bwmWidth)-col);
      if(ink) lcd.fillRect(52+col*3,144+(position/bwmWidth)*3,n*3,3,themes[theme].watermark);
      remaining-=n; position+=n;
    }
  }
}
void orientationScreen() {
  lcd.portraitAxes(orientations[orientationIndex]); orientationReadback=lcd.readRegister(0x0B);
  lcd.fillScreen(0);
  centered(0,24,320,"TOP",0x2EDF,4);
  label(12,100,"LEFT",0xEF7D); label(248,100,"RIGHT",0xEF7D);
  centered(0,157,320,"Q-MARAUDER",0xEF7D,3);
  centered(0,207,320,"ABC 123",0x2EDF,4);
  centered(0,285,320,"TAP ANYWHERE",0xEF7D);
  centered(0,317,320,"IF THIS IS UPRIGHT",0xEF7D);
  centered(0,349,320,"AND READS NORMALLY",0xEF7D,1);
  centered(0,410,320,"USB AT BOTTOM",0x2EDF);
  centered(0,452,320,String(orientationIndex+1)+" / 4",0x8492);
  orientationSince=millis();
}
void splash() {
  lcd.fillScreen(0);
  logo(25,125,bwmWidth,&bwmRuns[0][0],sizeof(bwmRuns)/4);
  logo(195,101,marauderWidth,&marauderRuns[0][0],sizeof(marauderRuns)/4);
  centered(0,55,320,"Q-MARAUDER",themes[theme].text,3);
  centered(0,352,320,"BWM x MARAUDER",themes[theme].accent);
  centered(0,396,320,"UNO Q / TOUCH CONSOLE",themes[theme].muted,1);
  delay(1000);
}
bool chooseOrientation(int value,bool restoring) {
  if(value<0 || value>3) return false;
  orientation=value; lcd.portraitAxes(value);
  touch.calibrated=false; calibrationStep=0; calibrationRestoreAllowed=restoring;
  splashPending=true; dirty=true; return true;
}
bool isBack(const MenuEntry &entry) { return strcmp(entry.title,"Back")==0; }
int countItems() { int n=0; for(const auto &e:menuEntries) if(e.menu==menu && !isBack(e))++n; return n; }
const MenuEntry &itemAt(int index) {
  for(const auto &e:menuEntries) if(e.menu==menu && !isBack(e) && index--==0) return e;
  return menuEntries[0];
}
void statusBar() {
  const auto &p=themes[theme]; lcd.fillRect(0,33,320,25,p.bg);
  label(14,38,String(p.name)+" / WIFI "+wifiCount+" / BLE "+bleCount,p.muted,1);
  lcd.fillCircle(300,41,4,connected?GREEN:RED); statusDirty=false;
}
void footerButton(int x,const char *title,bool enabled=true) {
  const auto &p=themes[theme];
  lcd.fillRoundRect(x,Layout::footerTop,96,Layout::footerHeight,6,p.panel);
  if(enabled) lcd.drawRoundRect(x,Layout::footerTop,96,Layout::footerHeight,6,p.accent);
  centered(x,440,96,title,enabled?p.text:p.muted);
}
void calibrationScreen() {
  const auto &p=themes[theme]; lcd.fillScreen(p.bg);
  centered(0,140,320,"TOUCH SETUP",p.accent);
  centered(0,176,320,"Tap the circle",p.text);
  centered(0,206,320,"then lift your finger",p.text);
  centered(0,255,320,String("TARGET ")+String(calibrationStep+1)+" OF 3",p.accent);
  centered(0,300,320,"Firm fingertip pressure",p.muted,1);
  centered(0,321,320,"This sets BOTH touch axes",p.muted,1);
  int x=calibrationStep==1?284:36,y=calibrationStep==2?424:56;
  lcd.fillCircle(x,y,28,p.panel); lcd.drawCircle(x,y,28,p.accent);
  lcd.drawCircle(x,y,20,p.accent); lcd.fillCircle(x,y,7,p.text);
}
void render() {
  if(orientation<0) { dirty=false; return; }
  unsigned long start=millis(); const auto &p=themes[theme];
  if(!touch.calibrated) calibrationScreen();
  else {
    lcd.fillScreen(p.bg);
    label(14,13,"Q-MARAUDER",p.text,2); lcd.fillRect(14,57,292,2,p.accent);
    bool detail=infoTitle.length()>0; int count=countItems(),first=page*Layout::pageSize;
    if(!detail) {
      for(int row=0;row<Layout::pageSize && first+row<count;++row)
        lcd.fillRoundRect(10,Layout::rowTop+row*Layout::rowStride,300,Layout::rowHeight,6,p.panel);
    }
    watermark();
    if(detail) {
      wrapped(16,76,infoTitle,p.accent,24,2);
      wrapped(20,145,infoText,p.text,23,11);
      footerButton(10,"BACK");
      centered(112,442,198,"TAP BACK TO RETURN",p.muted,1);
    } else {
      label(14,76,menuTitles[menu],p.text,2);
      label(14,100,"TAP AN ITEM TO OPEN",p.muted,1);
      label(270,100,String(page+1)+"/"+String((count+3)/4),p.accent,1);
      for(int row=0;row<Layout::pageSize && first+row<count;++row) {
        const auto &entry=itemAt(first+row); int y=Layout::rowTop+row*Layout::rowStride;
        bool themeItem=entry.action>=8 && entry.action<=10;
        if(themeItem) {
          label(24,y+12,entry.title,p.text,2);
          const char *captions[]={"RED / GRAPHITE","CRIMSON / STEEL","ICE / MIDNIGHT"};
          label(24,y+43,captions[entry.action-8],p.muted,1);
          if(theme==entry.action-8) { lcd.drawRoundRect(10,y,300,64,6,p.accent); label(252,y+43,"ACTIVE",p.accent,1); }
        } else {
          String title=entry.title;
          wrapped(24,y+(title.length()>23?10:16),title,p.text,23,2);
          if(entry.child<0 && entry.action==0) label(24,y+51,"PORT PLANNED",p.muted,1);
        }
      }
      footerButton(10,menu==0?"THEMES":"BACK");
      footerButton(112,"PREV",page>0); footerButton(214,"NEXT",(page+1)*4<count);
    }
    statusBar();
  }
  renderMs=millis()-start; dirty=false;
}
void openMenu(int target) { menu=target; page=0; infoTitle=""; infoText=""; dirty=true; }
void goBack() {
  if(infoTitle.length()) { infoTitle=""; infoText=""; dirty=true; return; }
  if(menu==0) { themeReturnMenu=0; openMenu(14); return; }
  if(menu==14) { openMenu(themeReturnMenu); return; }
  for(const auto &e:menuEntries) if(e.menu==menu && isBack(e)) { openMenu(e.child); return; }
  openMenu(0);
}
void activate(int target) {
  if(target==0) { goBack(); return; }
  if(target==1) { --page; dirty=true; return; }
  if(target==2) { ++page; dirty=true; return; }
  if(target<10 || target>13) return;
  const auto &entry=itemAt(page*4+target-10);
  if(entry.child>=0) { if(entry.child==14) themeReturnMenu=menu; openMenu(entry.child); }
  else if(entry.action>=8 && entry.action<=10) { theme=entry.action-8; themeChosen=true; dirty=true; }
  else if(entry.action==6) { touch.calibrated=false; calibrationStep=0; calibrationRestoreAllowed=false; dirty=true; }
  else {
    infoTitle=entry.title;
    if(entry.action==0) infoText="Port planned. This function has no UNO Q backend yet.";
    else if(entry.action==5 || entry.action==7)
      infoText=String("Portrait touch console. WiFi discoveries: ")+wifiCount+". BLE discoveries: "+bleCount+". Sessions: "+sessionCount+". "+(hasGps?"GPS fix. ":"No GPS fix. ")+headline;
    else if(!connected) infoText="Linux service is offline. Reconnect to run this task.";
    else if(pendingAction) infoText="A request is pending. Please wait.";
    else { pendingAction=entry.action; ++actionSequence; infoText="Request queued. "+headline; }
    dirty=true;
  }
}
void completeTap(int x,int y) {
  if(orientation<0) { if(millis()-orientationSince>=1000) chooseOrientation(orientations[orientationIndex],false); return; }
  if(!touch.calibrated) {
    calibrationRaw[calibrationStep*2]=x; calibrationRaw[calibrationStep*2+1]=y;
    if(++calibrationStep==3) {
      touch.set(calibrationRaw[0],calibrationRaw[1],calibrationRaw[2],calibrationRaw[3],calibrationRaw[4],calibrationRaw[5]);
      calibrationStep=0;
    }
    dirty=true; return;
  }
  int target=Layout::hit(touch.screenX(x,y),touch.screenY(x,y),countItems(),page,infoTitle.length()>0);
  if(target==pressedHit && target>=0) activate(target);
  else if(pressedHit>=0) dirty=true;
}
void pollTouch() {
  if(millis()-lastSample<25) return;
  lastSample=millis(); lastTouch=touch.sample(); lcd.restoreBus();
  if(!lastTouch.down) {
    stable=0;
    if(!releaseAt) releaseAt=millis();
    if(millis()-releaseAt>=100 && releasePending) {
      releasePending=false; completeTap(pressX,pressY); held=false; pressedHit=-1;
    }
    return;
  }
  releaseAt=0;
  if(!stable) { pressX=lastTouch.x; pressY=lastTouch.y; }
  else { pressX=(pressX*2+lastTouch.x)/3; pressY=(pressY*2+lastTouch.y)/3; }
  if(++stable<3 || held) return;
  held=true; releasePending=true;
  if(touch.calibrated) {
    pressedHit=Layout::hit(touch.screenX(pressX,pressY),touch.screenY(pressX,pressY),countItems(),page,infoTitle.length()>0);
    if(pressedHit>=10) lcd.drawRoundRect(10,Layout::rowTop+(pressedHit-10)*Layout::rowStride,300,64,6,themes[theme].accent);
  }
}
String protocol() { return "qm-display/5;portrait;direct-touch;themes"; }
String diagnostics() {
  return String("read_id=0x")+String(lcd.readId,HEX)+";render_ms="+renderMs+";uptime_ms="+millis()
      +";touch="+lastTouch.x+","+lastTouch.y+","+lastTouch.pressure+";menu="+menu+";page="+page
      +";orientation="+orientation+";theme="+theme+";calibration_step="+calibrationStep;
}
String panelRegisters() {
  return String("candidate=")+orientationIndex+";software_axes="+orientations[orientationIndex]
      +";madctl=0x"+String(orientationReadback,HEX)+";current=0x"+String(lcd.readRegister(0x0B),HEX);
}
String getOrientation() { return orientation<0?"unset":String(orientation); }
bool restoreOrientation(int value) { return orientation<0 && chooseOrientation(value,true); }
String getTheme() { return themeChosen?String(theme):"unset"; }
bool restoreTheme(int value) {
  if(themeChosen || value<0 || value>2) return false;
  theme=value; themeChosen=true; dirty=true; return true;
}
String calibration() {
  if(!touch.calibrated) return "uncalibrated";
  String result="v2"; for(int value:touch.raw) result+=String(",")+value; return result;
}
bool restoreCalibration(int x0,int y0,int x1,int y1,int x2,int y2) {
  if(!calibrationRestoreAllowed || orientation<0 || touch.calibrated || calibrationStep!=0) return false;
  bool result=touch.set(x0,y0,x1,y1,x2,y2); dirty=true; return result;
}
String action() { return String(actionSequence)+","+pendingAction; }
bool acknowledge(int seq,String message) {
  if(seq!=actionSequence || message.length()>120) return false;
  pendingAction=0; if(infoTitle.length()) { infoText=message; dirty=true; } return true;
}
bool update(int wifi,int ble,int sessions,bool gps,String status) {
  if(wifi<0 || wifi>9999 || ble<0 || ble>9999 || sessions<0 || sessions>9999 || status.length()>68) return false;
  statusDirty=statusDirty || status!=headline || !connected || wifi!=wifiCount || ble!=bleCount;
  wifiCount=wifi; bleCount=ble; sessionCount=sessions; hasGps=gps;
  headline=status; lastUpdate=millis(); connected=true; return true;
}
void setup() {
  lcd.begin(); analogReadResolution(10); orientationScreen();
  Serial1.begin(115200); Serial1.print("MCU starting RPC Bridge communication"); Serial1.flush();
  Bridge.begin();
  Bridge.provide_safe("qm.protocol",protocol); Bridge.provide_safe("qm.diagnostics",diagnostics);
  Bridge.provide_safe("qm.panelRegisters",panelRegisters); Bridge.provide_safe("qm.update",update);
  Bridge.provide_safe("qm.action",action); Bridge.provide_safe("qm.ack",acknowledge);
  Bridge.provide_safe("qm.calibration",calibration); Bridge.provide_safe("qm.restoreCalibration",restoreCalibration);
  Bridge.provide_safe("qm.orientation",getOrientation); Bridge.provide_safe("qm.restoreOrientation",restoreOrientation);
  Bridge.provide_safe("qm.theme",getTheme); Bridge.provide_safe("qm.restoreTheme",restoreTheme);
}
void loop() {
  if(connected && millis()-lastUpdate>15000) { connected=false; headline="Linux offline / data stale"; statusDirty=true; }
  if(orientation<0 && millis()-orientationSince>7000 && !lastTouch.down && !releasePending) {
    orientationIndex=(orientationIndex+1)%4; orientationScreen();
  }
  if(splashPending) { splashPending=false; splash(); dirty=true; }
  pollTouch();
  if(dirty) render();
  else if(statusDirty && orientation>=0 && touch.calibrated) statusBar();
  delay(5);
}
