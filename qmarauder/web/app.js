"use strict";
const $ = (id) => document.getElementById(id);
let state = null;
let view = "overview";
let lastFingerprint = "";
const elem = (tag, text, cls) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (cls) node.className = cls; return node; };
function showView(name) {
  view = name;
  document.querySelectorAll(".view").forEach(node => node.classList.toggle("active", node.id === name));
  document.querySelectorAll("nav button").forEach(node => node.classList.toggle("active", node.dataset.view === name));
}
document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => showView(button.dataset.view)));
document.querySelectorAll("[data-action]").forEach(button => button.addEventListener("click", () => action(button.dataset.action)));
async function action(name, parameters) {
  try {
    const response = await fetch("/api/action", {method:"POST", headers:{"Content-Type":"application/json", "X-QM-Request":"1"}, body:JSON.stringify({action:name, ...(parameters ? {parameters} : {})})});
    const result = await response.json();
    if (!response.ok) throw Error(result.error || "Request failed");
    if (name === "wifi" || name === "ble") showView(name);
    if (name.startsWith("ble-")) showView("ble");
    if (name.startsWith("mission")) showView("survey");
    await refresh();
  } catch(error) { showError(error.message); }
}
function showError(message) { $("error").textContent = message || ""; $("error").hidden = !message; }
function renderWifi() {
  const filter = $("wifi-filter").value.toLowerCase();
  const rows = state.wifi.filter(row => `${row.name} ${row.address} ${row.band}`.toLowerCase().includes(filter));
  $("wifi-rows").replaceChildren(...rows.map(row => {
    const tr = elem("tr");
    const name = elem("td", row.name || "Hidden SSID"); name.append(elem("small", row.address));
    const signal = elem("td"); const box = elem("div", undefined, "signal"); const meter = elem("meter"); meter.min=0; meter.max=100; meter.value=row.signal; meter.setAttribute("aria-label", `${row.signal}% signal`); box.append(meter, elem("span", `${row.signal}%`)); signal.append(box);
    tr.append(name, elem("td",row.band),elem("td",row.channel),signal,elem("td",row.security)); return tr;
  }));
  $("wifi-empty").hidden = rows.length > 0;
  $("wifi-empty").textContent = state.wifi.length ? "No networks match this filter." : "No observations. Start a Wi-Fi scan.";
}
function renderBle() {
  const target=state.settings?.target;
  $("ble-rows").replaceChildren(...state.ble.map(row => {
    const tr=elem("tr"), name=elem("td",row.name || "Unnamed advertiser"), details=elem("details"), metadata=elem("pre",JSON.stringify({address_type:row.address_type,uuids:row.uuids,manufacturer_data:row.manufacturer_data,service_data:row.service_data},null,2));
    name.append(elem("small",row.fingerprint || "Advertising metadata unavailable")); details.append(elem("summary","Advertising metadata"),metadata);name.append(details);
    const td=elem("td"),button=elem("button",target===row.address?"Selected":"Use as target","secondary");button.disabled=!!(state.busy||state.mission);button.onclick=()=>saveSettings({target:row.address});td.append(button);
    tr.append(name,elem("td",row.address),elem("td",row.rssi == null ? "—" : `${row.rssi} dBm`),td);return tr;
  }));
  $("ble-empty").hidden=state.ble.length>0;
  const selected=state.ble.find(row=>row.address===target);
  const description=target?`${selected?.name || "Selected device"} · ${target}`:"No device selected. Discover BLE, then tap Use as target.";
  $("ble-target-name").textContent=description;$("settings-target").textContent=description;
  $("ble-target-status").textContent=state.busy?.startsWith("ble-")?"WORKING":target?"TARGET SELECTED":"SELECT A DEVICE";
  document.querySelectorAll('[data-ble-op], [data-action="ble-foxhunt"], [data-action="ble-gatt"]').forEach(button=>button.disabled=!!(state.busy||state.mission||!target));
  const report=state.ble_lab;
  $("ble-lab-outcome").textContent=report?.error || (report?.state==="running"?"BLE job running. Results appear when the bounded window finishes.":report?.note || "Each GATT job opens its own connection and disconnects afterward. Pairing-dependent access may be refused by the device.");
  $("ble-json").textContent=report?JSON.stringify(report,null,2):"No BLE job yet.";
  const results=[];
  if(report?.state==="done" && report.action==="ble-foxhunt") {
    results.push(resultCard("Signal tracking",`${report.samples.length} fresh samples · latest ${report.latest ?? "—"} dBm · peak ${report.peak ?? "—"} dBm · ${report.trend}. RSSI is not a distance measurement.`));
  }
  if(report?.state==="done") (report.characteristics||[]).forEach(c=>{
    const card=resultCard(c.uuid,`${c.flags.join(" / ")} · service ${c.service}${c.value!==undefined?" · value "+c.value:""}${c.write_completed?" · write completed":""}`);
    const button=elem("button","Use UUID","secondary");button.onclick=()=>{$("ble-uuid").value=c.uuid;$("ble-uuid").focus();};card.append(button);results.push(card);
  });
  if(report?.notifications?.length) results.push(resultCard("Notifications",`${report.notifications.length} events saved in the JSON report and Field log.`));
  $("ble-result-list").replaceChildren(...results);
  $("detection-list").replaceChildren(...(state.detections||[]).map(row=>resultCard(row.name||row.address,`${row.matches.join("; ")} · ${row.rssi ?? "—"} dBm · ${row.note}`)));
  if(!(state.detections||[]).length) $("detection-list").append(elem("p","No watchlist matches in the last detector scan.","footnote"));
}
function resultCard(title, description) {const node=elem("article",undefined,"result-card");node.append(elem("h3",title),elem("p",description));return node;}
async function saveSettings(values) {
  try {
    const response=await fetch("/api/settings",{method:"POST",headers:{"Content-Type":"application/json","X-QM-Request":"1"},body:JSON.stringify(values)});
    const result=await response.json();if(!response.ok)throw Error(result.error||"Settings could not be saved");
    await refresh();return true;
  } catch(error){showError(error.message);return false;}
}
function renderSettings() {
  const preferences=state.settings||{theme:0,rules:[],adapter:"hci0"};
  document.body.dataset.theme=preferences.theme;
  document.querySelectorAll('.theme-card').forEach(button=>{const active=Number(button.dataset.theme)===preferences.theme;button.classList.toggle("selected",active);button.setAttribute("aria-pressed",active);});
  $("theme-status").textContent=state.pending_theme!=null?"SAVED · WAITING FOR TFT":"SAVED";
  $("ble-adapter").value=preferences.adapter;$("ble-adapter").disabled=!!(state.busy||state.mission);
  $("rule-count").textContent=`${preferences.rules.length} / 32 RULES`;
  $("rule-list").replaceChildren(...preferences.rules.map((rule,index)=>{const row=resultCard(rule.label,`${rule.kind} · ${rule.value}`),button=elem("button","Remove","secondary");button.disabled=!!(state.busy||state.mission);button.onclick=()=>saveSettings({rules:state.settings.rules.filter((_,i)=>i!==index)});row.append(button);return row;}));
  $("watchlist-form").querySelectorAll("input,select,button").forEach(input=>input.disabled=!!(state.busy||state.mission));
}
document.querySelectorAll('[data-theme]').forEach(button=>button.onclick=()=>saveSettings({theme:Number(button.dataset.theme)}));
document.querySelectorAll('[data-ble-op]').forEach(button=>button.onclick=()=>action(button.dataset.bleOp,{uuid:$("ble-uuid").value.trim(),...(button.dataset.bleOp==="ble-write"?{value:$("ble-value").value.trim(),write_type:$("ble-write-type").value}:{})}));
$("clear-ble-target").onclick=()=>saveSettings({target:""});
$("ble-adapter").onchange=()=>saveSettings({adapter:$("ble-adapter").value});
$("watchlist-form").onsubmit=async(event)=>{event.preventDefault();if(!state)return;const rule={label:$("rule-label").value.trim(),kind:$("rule-kind").value,value:$("rule-value").value.trim()};if(await saveSettings({rules:[...state.settings.rules,rule]})){ $("rule-label").value="";$("rule-value").value=""; }};
function renderChart() {
  if (!state.wifi.length) return;
  const counts = new Map(); state.wifi.forEach(row => counts.set(row.channel,(counts.get(row.channel)||0)+1));
  const entries = [...counts.entries()].sort((a,b)=>a[0]-b[0]);
  const ns="http://www.w3.org/2000/svg";
  const svg=document.createElementNS(ns,"svg"); svg.setAttribute("viewBox","0 0 520 150"); svg.setAttribute("role","img"); svg.setAttribute("aria-label","Observed access points per Wi-Fi channel");
  const add=(tag,attrs,text)=>{const node=document.createElementNS(ns,tag); Object.entries(attrs).forEach(([k,v])=>node.setAttribute(k,v)); if(text!==undefined)node.textContent=text; svg.append(node);};
  const max=Math.max(...entries.map(x=>x[1]),1), width=480/entries.length;
  for(let y=0;y<3;y++)add("line",{x1:20,x2:510,y1:15+y*50,y2:15+y*50});
  entries.forEach(([channel,count],i)=>{const x=25+i*width,h=count/max*90;add("rect",{x,y:115-h,width:Math.max(4,width-9),height:h,rx:1,class:channel>14?"five":""});add("text",{x:x+(width-9)/2,y:136,"text-anchor":"middle"},channel);add("text",{x:x+(width-9)/2,y:109-h,"text-anchor":"middle"},count);});
  $("channel-chart").replaceChildren(svg);
}
function renderSessions() {
  $("session-list").replaceChildren(...state.sessions.map(session=>{const box=elem("article",undefined,"session"),text=elem("div"),links=elem("div");text.append(elem("h3",`${session.mode.toUpperCase()} / ${new Date(session.started).toLocaleString()}`),elem("p",`${session.observations} observations · ${session.geotagged} geotagged · ${session.ended ? "Closed" : "Recording"}`));["csv","json"].forEach(fmt=>{const a=elem("a",fmt.toUpperCase()+" ↓");a.href=`/api/export/${session.id}.${fmt}`;a.download="";links.append(a);});box.append(text,links);return box;}));
  if(!state.sessions.length)$("session-list").append(elem("p","Your survey sessions will appear here.","empty"));
}
function renderModules() {
  const filter=$("module-filter").value.toLowerCase();
  const features=state.features.filter(item=>`${item.name} ${item.category} ${item.detail}`.toLowerCase().includes(filter));
  $("module-count").textContent=`${features.length} capabilities`;
  $("module-list").replaceChildren(...features.map(item=>{const box=elem("article",undefined,"module");box.append(elem("div",item.category.toUpperCase(),"category"),elem("span",item.status.toUpperCase(),`badge ${item.status}`),elem("h3",item.name),elem("p",item.detail));if(item.source){const link=elem("a","Upstream reference ↗");link.href=item.source;link.target="_blank";link.rel="noopener noreferrer";box.append(link);}return box;}));
}
function renderDiagnostics() {
  const c=state.capabilities;
  const entries=[
    ["RADIO DRIVER",c.interfaces.map(x=>x.driver).join(", ")||"Not detected",c.interfaces.map(x=>x.name).join(", ")||"Run on the UNO Q"],
    ["MONITOR MODE",c.monitor_advertised===null?"Unknown":c.monitor_advertised?"Advertised":"Not advertised","Advertisement does not prove packet reception"],
    ["PACKET INJECTION",state.lab?.injection_observed ? "Observed in last test" : "Not verified","Needs a successful directed-response test; see the lab report"],
    ["TFT DISPLAY",state.display?.connected?"Native portrait UI":"Not connected",state.display?.error || (state.display?.connected?"320 x 480 / direct touch / "+state.display.touch:"Install the UNO shield MCU target")],
    ["GPS RECEIVER",state.gps?"Fresh fix":"No fix","Local gpsd · coordinates never fabricated"],
    ["PLATFORM",c.platform,"Debian service + separate MCU display firmware"],
    ["USB RADIO DRIVER",c.interfaces.some(x=>x.driver === "mt7921u") ? "MT7921 USB attached" : c.kernel?.modules?.mt7921u?.available ? "MT7921 module installed" : c.kernel?.options?.MT7921U === "disabled" ? "MT7921 USB missing" : ["y","m"].includes(c.kernel?.options?.MT7921U) ? "MT7921 USB configured" : "Not measured","PC forwarding must remain connected; use Lab report for measured RF results"],
    ["LAB HELPER",c.lab?.configured ? "Configured" : "Setup required",c.lab?.reason || "Fixed, bounded jobs for your configured lab AP"]
  ];
  $("diagnostics").replaceChildren(...entries.map(([label,value,note])=>{const box=elem("article",undefined,"diagnostic");box.append(elem("label",label),elem("strong",value),elem("p",note));return box;}));
  $("iw-evidence").textContent=c.iw_evidence;
}
function renderLab() {
  const report=state.lab;
  $("lab-status").textContent=report?.state === "running" ? "RUNNING" : report?.state === "error" ? "TEST ERROR" : report ? "LAST TEST" : "NO TEST YET";
  $("lab-outcome").textContent=report?.error || report?.note || (report?.state === "running" ? "Test in progress. The result will appear here." : "Tests use the configured lab access point. Results stay on this device.");
  const values=report?.state === "done" ? [["RECEIVE PACKETS",report.received ?? 0],["LAB FRAMES",report.frames ?? 0],["SUBMITTED",report.sent ?? 0],["DIRECTED REPLIES",report.probe_responses ?? 0]] : [];
  $("lab-metrics").replaceChildren(...values.map(([label,value])=>{const card=elem("div");card.append(elem("small",label),elem("strong",value));return card;}));
  document.querySelectorAll("[data-action^='lab-']").forEach(button=>{button.disabled ||= !state.capabilities.lab?.configured;});
}
function render() {
  $("ap-count").textContent=state.wifi.length || (state.updated ? "0":"—");
  $("ble-count").textContent=state.ble.length || (state.updated ? "0":"—");
  $("session-count").textContent=state.sessions.length;
  $("gps-status").textContent=state.gps?"FIX LOCKED":"NO FIX";
  $("gps-detail").textContent=state.gps?`${state.gps.lat.toFixed(5)}, ${state.gps.lon.toFixed(5)}`:"Connect a gpsd receiver";
  $("activity").textContent=state.stopping?"STOPPING":state.busy?state.busy.toUpperCase():state.mission?"SURVEY RUNNING":"READY";
  $("activity-dot").classList.toggle("working",!!state.busy);
  $("last-update").textContent=state.updated?`LAST OBSERVATION ${new Date(state.updated).toLocaleTimeString()}`:"No radio tasks have run";
  $("wifi-updated").textContent=`${state.wifi.length} access points`;
  $("mission-button").textContent=state.mission?"Stop survey ■":"Start survey ↗";
  $("mission-button").dataset.action=state.mission?"mission-stop":"mission-start";
  $("mission-status").textContent=state.stopping?"STOPPING":state.mission?"RECORDING":"STANDBY";
  document.querySelectorAll("[data-action]").forEach(button=>{button.disabled=button.dataset.action==="mission-stop"?state.stopping:!!(state.busy||state.mission);});
  showError(state.error);
  renderSettings();renderWifi();renderBle();renderChart();renderSessions();renderModules();renderDiagnostics();renderLab();
}
async function refresh() {
  try {
    const response=await fetch("/api/state",{cache:"no-store"});
    if(!response.ok)throw Error("Device is unavailable");
    const next=await response.json();
    const fingerprint=JSON.stringify(next);
    state=next;
    $("connection").textContent="DEVICE ONLINE";
    if(fingerprint!==lastFingerprint){render();lastFingerprint=fingerprint;}
  } catch(error) { $("connection").textContent="OFFLINE"; showError("Cannot reach the console. Check the service or USB connection."); }
}
$("wifi-filter").addEventListener("input",()=>state&&renderWifi());
$("module-filter").addEventListener("input",()=>state&&renderModules());
setTimeout(()=>{$("boot").classList.add("hide");setTimeout(()=>$("boot").remove(),600);},1800);
setInterval(()=>$("clock").textContent=new Date().toLocaleTimeString([], {hour12:false}),1000);
async function poll(){await refresh();setTimeout(poll,1800);}poll();
