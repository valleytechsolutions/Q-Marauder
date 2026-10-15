"""Refresh native menu labels from the pinned, locally inspected Marauder source.

This imports labels only, never upstream radio implementations. Generated data is
checked in so users do not need the upstream checkout to build the firmware.
"""
import json
import re
from pathlib import Path

root=Path(__file__).resolve().parents[1]
upstream=root/".upstream/marauder/esp32_marauder"
language=(upstream/"lang_var.h").read_text(encoding="utf-8")
labels=dict(re.findall(r'const char (\w+)\[\]\s*=\s*"([^"\n]*)"',language))
source=(upstream/"MenuFunctions.cpp").read_text(encoding="utf-8")
source=re.sub(r'/\*.*?\*/','',source,flags=re.S)
source=re.sub(r'//[^\n]*','',source)
menus=[("mainMenu","Main menu",0), ("wifiMenu","Wi-Fi",0),
       ("wifiSnifferMenu","Wi-Fi / Sniffers",1), ("wifiScannerMenu","Wi-Fi / Scanners",1),
       ("wifiAttackMenu","Wi-Fi / Attacks",1), ("wifiGeneralMenu","Wi-Fi / General",1),
       ("bluetoothMenu","Bluetooth",0), ("bluetoothSnifferMenu","Bluetooth / Sniffers",6),
       ("bluetoothAttackMenu","Bluetooth / Attacks",6), ("gpsMenu","GPS",0),
       ("deviceMenu","Device",0), ("reconMenu","Recon / Wardriving",0),
       ("settingsMenu","Settings",10), ("detectorsMenu","Counter surveillance",0),
       ("themesMenu","Appearance",12)]
links={(0,"WiFi"):1,(0,"Bluetooth"):6,(0,"GPS"):9,(0,"Device"):10,(0,"Recon"):11,
       (1,"Sniffers"):2,(1,"Scanners"):3,(1,"Attacks"):4,(1,"General"):5,
       (6,"Sniffers"):7,(6,"Bluetooth Attacks"):8,(10,"Settings"):12,
       (0,"Counter surveillance"):13,(12,"Themes"):14}
# IDs 1-4 and 14-17 invoke Linux jobs; the others are local display actions.
actions={"Scan APs":1,"Bluetooth Sniffer":2,"Wardrive":3,"Stop survey":4,
         "Device Info":5,"Calibrate touch":6,"Live status":7,
         "BWM":8,"Marauder":9,"Biscuit Shop":10,"Valleytech":11,
         "Wi-Fi results":12,"BLE results":13,"Scan BLE":2,"Test readiness":14,
         "Lab packet recon":15,"Injection check":16,"Lab deauth (3 frames)":17}
entries=[]
for index,(key,title,parent) in enumerate(menus):
    found=[]
    for expression in re.findall(r'addNodes\(&'+key+r',\s*("[^"\n]*"|text_table1\[\d+\]|text\w+)',source):
        if expression.startswith('"'): value=expression[1:-1]
        else:
            match=re.fullmatch(r'text_table1\[(\d+)\]',expression)
            value=labels.get("text1_"+match[1] if match else expression,"")
        value=value.strip()
        if value and value not in found: found.append(value)
    if index==0: found=["Recon","WiFi","Bluetooth","GPS","Device","Counter surveillance","Reboot"]
    if index==3: found.insert(1,"Scan APs")
    if index==1: found[1:1]=["Scan APs","Wi-Fi results"]
    if index==6: found[1:1]=["Scan BLE","BLE results"]
    if index in (4,8): found.insert(1,"Test readiness")
    if index==2: found.insert(1,"Lab packet recon")
    if index==4: found[2:2]=["Injection check","Lab deauth (3 frames)"]
    if index==11: found=["Back","Wardrive","Stop survey","Live status"]
    if index==12: found=["Back","Themes","Calibrate touch"]
    if index==13: found=["Back","Dragon Detector","Axeoff","Squachwach"]
    if index==14: found=["Back","BWM","Marauder","Biscuit Shop","Valleytech"]
    if index==10 and "Calibrate touch" not in found: found.append("Calibrate touch")
    if index and "Back" not in found: found.insert(0,"Back")
    for value in found:
        target=parent if value=="Back" else links.get((index,value),-1)
        entries.append((index,value,target,actions.get(value,0)))
lines=["// Generated menu labels from Marauder; upstream MIT notice in licenses/.",
       "#pragma once", "struct MenuEntry { uint8_t menu; const char *title; int8_t child; uint8_t action; };",
       "const char *const menuTitles[] = {"+','.join(json.dumps(title) for _,title,_ in menus)+"};",
       "const MenuEntry menuEntries[] = {"]
lines += ["  {%d,%s,%d,%d},"%(m,json.dumps(title),child,action) for m,title,child,action in entries]
lines += ["};",f"constexpr int MENU_ENTRY_COUNT = {len(entries)};"]
(root/"firmware/uno_shield/MenuData.h").write_text('\n'.join(lines)+'\n',encoding="ascii")
print(f"Generated {len(entries)} selections across {len(menus)} menus")
