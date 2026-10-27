"use strict";
const captures = new Map();
const LIMIT = 150;
function stateFor(tabId) {
  if (!captures.has(tabId)) captures.set(tabId, {rows:new Map(), inspections:new Map(), autoScans:0});
  return captures.get(tabId);
}
function updateBadge(tabId) {
  browser.browserAction.setBadgeText({tabId,text:captures.get(tabId)?.rows.size ? String(captures.get(tabId).rows.size) : ""}).catch(() => {});
}
function clearTab(tabId) {
  const state = captures.get(tabId);
  if (state) for (const controller of state.inspections.values()) controller.abort();
  captures.delete(tabId);
}
function putRow(state, key, row) {
  state.rows.delete(key); state.rows.set(key,row);
  while (state.rows.size > LIMIT) state.rows.delete(state.rows.keys().next().value);
}
async function readPlaylist(response) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let size = 0, text = "";
  try {
    while (true) {
      const {done,value} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 2097152) throw new Error("Playlist exceeds the 2 MB inspection limit.");
      text += decoder.decode(value,{stream:true});
    }
    return text + decoder.decode();
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
async function inspectPlaylist(tabId, row, force=false) {
  const state = captures.get(tabId);
  if (!state || state.inspections.has(row.url) || (!force && row.inspection)) return;
  const controller = new AbortController();
  state.inspections.set(row.url,controller);
  row.inspection = "Looking for audio tracks…";
  const timeout = setTimeout(() => controller.abort(),15000);
  try {
    const response = await fetch(row.url,{credentials:"include",cache:"force-cache",signal:controller.signal});
    if (!response.ok) throw new Error("HTTP " + response.status);
    const parsed = parseHlsTracks(await readPlaylist(response),response.url || row.url);
    if (captures.get(tabId) !== state) return;
    for (const track of parsed.tracks) {
      const key = "GET " + track.url;
      const old = state.rows.get(key);
      putRow(state,key,{
        ...old, url:track.url,host:new URL(track.url).hostname,
        mime:old?.mime || "application/vnd.apple.mpegurl",
        kind:"Playlist",role:track.role,trackName:track.name,language:track.language,group:track.group,
        method:"GET",status:old?.status ?? null,discovered:true,
        parentUrl:row.url,count:old?.count || 0,seen:Date.now()
      });
    }
    const audioCount = parsed.tracks.filter(track => track.role === "audio").length;
    row.inspection = audioCount ? "Found " + audioCount + " audio playlist(s)." : parsed.master ? "No separate audio URI found in this master playlist. Audio may be included in a variant." : "This is a media playlist; it does not list a separate audio track.";
    updateBadge(tabId);
  } catch (error) {
    if (captures.get(tabId) === state) row.inspection = "Audio discovery failed: " + (error.name === "AbortError" ? "request timed out or was cancelled" : error.message);
  } finally { clearTimeout(timeout); state.inspections.delete(row.url); }
}
browser.browserAction.setBadgeBackgroundColor({color:"#2563eb"});
browser.webRequest.onHeadersReceived.addListener(details => {
  if (details.tabId < 0 || details.originUrl?.startsWith(browser.runtime.getURL(""))) return;
  let url;
  try { url = new URL(details.url); } catch { return; }
  const header = name => (details.responseHeaders || []).find(h => h.name.toLowerCase() === name)?.value || "";
  const mime = header("content-type").split(";")[0].trim().toLowerCase();
  const youtube = (url.hostname === "googlevideo.com" || url.hostname.endsWith(".googlevideo.com")) && url.pathname.endsWith("/videoplayback");
  const hls = /\.m3u8$/i.test(url.pathname) || /mpegurl/.test(mime);
  const playlist = hls || /\.mpd$/i.test(url.pathname) || /dash\+xml/.test(mime);
  const hintedMime = url.searchParams.get("mime") || "";
  const directAudio = !playlist && mime !== "application/vnd.yt-ump" && (mime.startsWith("audio/") || (youtube && hintedMime.startsWith("audio/")));
  if (!youtube && !playlist && !/^(audio|video)\//.test(mime) && details.type !== "media") return;
  const state = stateFor(details.tabId);
  const key = details.method + " " + details.url;
  const old = state.rows.get(key);
  const row = Object.assign(old || {}, {
    ...old,url:details.url,host:url.hostname,mime:mime || "unknown",
    kind:playlist ? "Playlist" : directAudio ? "Audio" : mime.startsWith("video/") ? "Video" : "Media",
    role:directAudio ? "audio" : old?.role || (mime.startsWith("video/") && !playlist ? "video" : "unknown"),
    method:details.method,status:details.statusCode,range:header("content-range"),
    itag:youtube ? url.searchParams.get("itag") : null,count:(old?.count || 0)+1,seen:Date.now()
  });
  putRow(state,key,row); updateBadge(details.tabId);
  if (hls && details.method === "GET" && details.statusCode >= 200 && details.statusCode < 300 && !row.inspection && state.autoScans < 12) {
    state.autoScans++; void inspectPlaylist(details.tabId,row);
  }
},{urls:["http://*/*","https://*/*"]},["responseHeaders"]);
browser.tabs.onRemoved.addListener(clearTab);
browser.tabs.onUpdated.addListener((tabId,change) => {
  if (change.status === "loading") { clearTab(tabId); updateBadge(tabId); }
});
browser.runtime.onMessage.addListener((message,sender) => {
  if (sender.id !== browser.runtime.id || !Number.isInteger(message.tabId)) return;
  const list = () => Array.from(captures.get(message.tabId)?.rows.values() || []).reverse();
  if (message.type === "list") return Promise.resolve(list());
  if (message.type === "discoverAudio") return (async () => {
    const rows = list().filter(row => row.method === "GET" && /mpegurl/.test(row.mime) && row.status >= 200 && row.status < 300).slice(0,12);
    for (let i=0;i<rows.length;i+=3) await Promise.all(rows.slice(i,i+3).map(row => inspectPlaylist(message.tabId,row,true)));
    return list();
  })();
  if (message.type === "clear") { clearTab(message.tabId); updateBadge(message.tabId); return Promise.resolve([]); }
});
