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
async function action(name) {
  try {
    const response = await fetch("/api/action", {method:"POST", headers:{"Content-Type":"application/json", "X-QM-Request":"1"}, body:JSON.stringify({action:name})});
    const result = await response.json();
    if (!response.ok) throw Error(result.error || "Request failed");
    if (name === "wifi" || name === "ble") showView(name);
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
  $("ble-rows").replaceChildren(...state.ble.map(row => { const tr=elem("tr"); tr.append(elem("td",row.name || "Unnamed advertiser"),elem("td",row.address),elem("td",row.rssi == null ? "—" : `${row.rssi} dBm`)); return tr; }));
  $("ble-empty").hidden = state.ble.length > 0;
}
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
  renderWifi();renderBle();renderChart();renderSessions();renderModules();renderDiagnostics();renderLab();
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
