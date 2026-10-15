// SPDX-License-Identifier: MIT
#include <Arduino_RouterBridge.h>
#include "Parallel9486.h"
#include "TouchControls.h"
#include "LogoData.h"
#include "MenuData.h"

Parallel9486 lcd;
TouchControls touch;
constexpr uint16_t BG=0x0841, PANEL=0x10A3, CYAN=0x07BF, WHITE=0xEF7D;
constexpr uint16_t MUTED=0x8492, RED=0xF920, GREEN=0x47E9;
String headline="Waiting for Linux", infoTitle="", infoText="";
int wifiCount=0, bleCount=0, sessionCount=0, menu=0, selection=0;
int pendingAction=0, actionSequence=0, calibrationStep=0, topX=0, topY=0;
bool hasGps=false, connected=false, dirty=true, held=false, released=true;
unsigned long lastUpdate=0, lastSample=0, releaseAt=0;
int stable=0;
uint32_t renderMs=0;
TouchSample lastTouch={0,0,0,false};
int drawnMenu=-1, drawnSelection=-1, drawnPage=-1;
const uint8_t orientations[]={1,3,0,2}; // Software X/Y reflections, not MADCTL bytes.
int orientation=-1, orientationIndex=0;
unsigned long orientationSince=0;
uint32_t orientationReadback=0;
bool splashPending=false, calibrationRestoreAllowed=false;

void label(int x,int y,const String &value,uint16_t color,uint8_t size=2) {
  lcd.setCursor(x,y); lcd.setTextColor(color); lcd.setTextSize(size); lcd.print(value);
}
void wrapped(int x,int y,String value,uint16_t color,int columns=23,int maxLines=2) {
  for(int line=0;line<maxLines && value.length();++line) {
    int n=min(int(value.length()),columns);
    if(int(value.length())>columns) {
      int space=value.lastIndexOf(' ',columns);
      if(space>columns/2) n=space;
    }
    label(x,y+line*20,value.substring(0,n),color);
    value=value.substring(n); value.trim();
  }
}
void logo(int x,int y,int width,const uint16_t *runs,size_t count) {
  uint32_t position=0;
  for(size_t i=0;i<count;++i) {
    uint16_t remaining=runs[i*2];
    while(remaining) {
      uint16_t col=position%width, n=min(int(remaining),width-col);
      lcd.fillRect(x+col*2,y+(position/width)*2,n*2,2,runs[i*2+1]);
      remaining-=n; position+=n;
    }
  }
}
void orientationScreen() {
  lcd.portraitAxes(orientations[orientationIndex]);
  orientationReadback=lcd.readRegister(0x0B);
  lcd.fillScreen(0);
  label(124,24,"TOP",CYAN,4);
  label(12,100,"LEFT",WHITE,2); label(248,100,"RIGHT",WHITE,2);
  label(70,157,"Q-MARAUDER",WHITE,3);
  label(76,207,"ABC 123",CYAN,4);
  label(76,285,"TAP ANYWHERE",WHITE,2);
  label(52,317,"IF THIS IS UPRIGHT",WHITE,2);
  label(70,349,"AND READS NORMALLY",WHITE,1);
  label(82,410,"USB AT BOTTOM",CYAN,2);
  label(124,452,String(orientationIndex+1)+" / 4",MUTED,2);
  orientationSince=millis();
}
void splash() {
  lcd.fillScreen(0);
  logo(25,125,bwmWidth,&bwmRuns[0][0],sizeof(bwmRuns)/4);
  logo(195,101,marauderWidth,&marauderRuns[0][0],sizeof(marauderRuns)/4);
  label(40,55,"Q-MARAUDER",WHITE,3);
  label(40,352,"BWM x MARAUDER",CYAN,2);
  label(55,396,"UNO Q / NATIVE CONSOLE",MUTED,1);
  delay(1500);
}
bool chooseOrientation(int value,bool restoring) {
  if(value<0 || value>3) return false;
  orientation=value; lcd.portraitAxes(value);
  touch.calibrated=false; calibrationStep=0; calibrationRestoreAllowed=restoring;
  drawnMenu=-1; splashPending=true; dirty=true;
  return true;
}
int countItems() { int n=0; for(const auto &e:menuEntries) if(e.menu==menu)++n; return n; }
const MenuEntry &itemAt(int index) {
  for(const auto &e:menuEntries) if(e.menu==menu && index--==0) return e;
  return menuEntries[0];
}
void chrome() {
  lcd.fillScreen(BG);
  lcd.fillRect(0,0,320,72,PANEL); lcd.fillRect(0,0,320,3,CYAN);
  lcd.fillTriangle(34,24,24,40,44,40,CYAN); label(122,27,"UP",WHITE,3);
  lcd.fillRect(0,416,320,64,PANEL); lcd.fillRect(0,477,320,3,CYAN);
  lcd.fillTriangle(34,457,24,441,44,441,CYAN); label(104,437,"DOWN",WHITE,3);
  label(14,84,"Q-MARAUDER",WHITE,2);
}
void render() {
  if(orientation<0) { dirty=false; return; }
  unsigned long start=millis();
  bool menuVisible=touch.calibrated && !infoTitle.length();
  int page=selection/5;
  bool full=!menuVisible || drawnMenu!=menu || drawnPage!=page;
  if(full) lcd.fillRect(0,108,320,308,BG);
  if(!touch.calibrated) {
    label(14,119,"TOUCH SETUP",CYAN,2);
    wrapped(20,177,calibrationStep==0?"Press and release the TOP pad":"Press and release the BOTTOM pad",WHITE,22,3);
    wrapped(20,272,"Use a firm fingertip press.",MUTED,22,2);
    label(20,344,calibrationStep==0?"STEP 1 / 2":"STEP 2 / 2",CYAN,2);
  } else if(infoTitle.length()) {
    wrapped(16,124,infoTitle,CYAN,23,2);
    wrapped(16,186,infoText,WHITE,23,8);
    label(16,391,"CENTER: RETURN",MUTED,1);
  } else {
    label(14,112,menuTitles[menu],CYAN,1);
    int count=countItems(), first=(selection/5)*5;
    for(int i=first;i<min(first+5,count);++i) {
      if(!full && i!=selection && i!=drawnSelection) continue;
      if(!full && selection==drawnSelection) continue;
      const auto &entry=itemAt(i); int y=132+(i-first)*49;
      bool selected=i==selection;
      lcd.fillRect(10,y,300,45,selected?CYAN:PANEL);
      String title=String(selected?"> ":"  ")+entry.title;
      wrapped(17,y+(title.length()>23?3:13),title,selected?BG:WHITE,23,2);
      if(entry.child<0 && entry.action==0) lcd.fillRect(303,y+19,3,7,selected?BG:MUTED);
    }
    lcd.fillRect(0,380,320,36,BG);
    label(14,385,String(selection+1)+" / "+String(count)+"   CENTER: SELECT",MUTED,1);
    label(14,401,headline.substring(0,46),connected?GREEN:MUTED,1);
  }
  lcd.fillRect(298,88,8,8,connected?GREEN:RED);
  drawnMenu=menuVisible?menu:-1; drawnSelection=selection; drawnPage=page;
  renderMs=millis()-start; dirty=false;
}
void navigate(int zone) {
  if(infoTitle.length()) { infoTitle=""; infoText=""; dirty=true; return; }
  int count=countItems();
  if(zone<0) selection=(selection+count-1)%count;
  else if(zone>0) selection=(selection+1)%count;
  else {
    const auto &entry=itemAt(selection);
    if(entry.child>=0) { menu=entry.child; selection=0; }
    else if(entry.action==6) { touch.calibrated=false; calibrationStep=0; calibrationRestoreAllowed=false; }
    else {
      infoTitle=entry.title;
      if(entry.action==0) infoText="Port planned. This function has no UNO Q backend yet.";
      else if(entry.action==5 || entry.action==7) {
        infoText=String("ILI9486 / 320 x 480. WiFi: ")+wifiCount+" BLE: "+bleCount+" Sessions: "+sessionCount+". "+(hasGps?"GPS fix. ":"No GPS fix. ")+headline;
      } else if(!connected) infoText="Linux service is offline. Reconnect to run this task.";
      else if(pendingAction) infoText="A request is pending. Please wait.";
      else { pendingAction=entry.action; ++actionSequence; infoText="Request queued. "+headline; }
    }
  }
  dirty=true;
}
void pollTouch() {
  if(millis()-lastSample<35) return;
  lastSample=millis(); lastTouch=touch.sample(); lcd.restoreBus();
  if(!lastTouch.down) {
    stable=0;
    if(!releaseAt) releaseAt=millis();
    if(millis()-releaseAt>120) { held=false; released=true; }
    return;
  }
  releaseAt=0;
  if(held || !released || ++stable<3) return;
  held=true; released=false;
  if(orientation<0) {
    if(millis()-orientationSince>=1000) chooseOrientation(orientations[orientationIndex],false);
    return;
  }
  if(!touch.calibrated) {
    if(calibrationStep==0) { topX=lastTouch.x; topY=lastTouch.y; calibrationStep=1; }
    else {
      int axis=abs(lastTouch.x-topX)>abs(lastTouch.y-topY)?0:1;
      if(!touch.set(axis,axis?topY:topX,axis?lastTouch.y:lastTouch.x)) calibrationStep=0;
    }
    dirty=true;
  } else {
    int y=touch.screenY(lastTouch); navigate(y<72?-1:y>=416?1:0);
  }
}
String protocol() { return "qm-display/4;portrait;three-zone-touch;software-orientation"; }
String diagnostics() {
  return String("read_id=0x")+String(lcd.readId,HEX)+";render_ms="+renderMs+";uptime_ms="+millis()
      +";touch="+lastTouch.x+","+lastTouch.y+","+lastTouch.pressure+";menu="+menu+";selection="+selection
      +";orientation="+orientation;
}
String panelRegisters() {
  return String("candidate=")+orientationIndex+";software_axes="+orientations[orientationIndex]
      +";madctl=0x"+String(orientationReadback,HEX)+";current=0x"+String(lcd.readRegister(0x0B),HEX);
}
String getOrientation() { return orientation<0?"unset":String(orientation); }
bool restoreOrientation(int value) {
  return orientation<0 && chooseOrientation(value,true);
}
String calibration() {
  return touch.calibrated?String(touch.axis)+","+touch.top+","+touch.bottom:"uncalibrated";
}
bool restoreCalibration(int axis,int top,int bottom) {
  if(!calibrationRestoreAllowed || orientation<0 || touch.calibrated || calibrationStep!=0) return false;
  bool result=touch.set(axis,top,bottom); dirty=true; return result;
}
String action() { return String(actionSequence)+","+pendingAction; }
bool acknowledge(int seq,String message) {
  if(seq!=actionSequence || message.length()>120) return false;
  pendingAction=0; infoText=message; dirty=true; return true;
}
bool update(int wifi,int ble,int sessions,bool gps,String status) {
  if(wifi<0 || wifi>9999 || ble<0 || ble>9999 || sessions<0 || sessions>9999 || status.length()>68) return false;
  dirty=dirty || status!=headline || !connected;
  wifiCount=wifi; bleCount=ble; sessionCount=sessions; hasGps=gps;
  headline=status; lastUpdate=millis(); connected=true; return true;
}
void setup() {
  lcd.begin(); analogReadResolution(10);
  orientationScreen();
  // Flush partial serial frames on the older factory core before registering RPC.
  Serial1.begin(115200); Serial1.print("MCU starting RPC Bridge communication"); Serial1.flush();
  Bridge.begin();
  Bridge.provide_safe("qm.protocol",protocol);
  Bridge.provide_safe("qm.diagnostics",diagnostics);
  Bridge.provide_safe("qm.panelRegisters",panelRegisters);
  Bridge.provide_safe("qm.update",update);
  Bridge.provide_safe("qm.action",action);
  Bridge.provide_safe("qm.ack",acknowledge);
  Bridge.provide_safe("qm.calibration",calibration);
  Bridge.provide_safe("qm.restoreCalibration",restoreCalibration);
  Bridge.provide_safe("qm.orientation",getOrientation);
  Bridge.provide_safe("qm.restoreOrientation",restoreOrientation);
}
void loop() {
  if(connected && millis()-lastUpdate>15000) { connected=false; headline="Linux offline / data stale"; dirty=true; }
  if(orientation<0 && millis()-orientationSince>7000 && !lastTouch.down) {
    orientationIndex=(orientationIndex+1)%4; orientationScreen();
  }
  if(splashPending) { splashPending=false; splash(); chrome(); dirty=true; }
  pollTouch();
  if(dirty) render();
  delay(5);
}
