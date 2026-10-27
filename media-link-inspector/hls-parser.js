"use strict";
function hlsAttributes(text) {
  const result = {};
  const pattern = /([A-Z0-9-]+)=("(?:[^"]*)"|[^,]*)/g;
  let match;
  while ((match = pattern.exec(text))) result[match[1]] = match[2].replace(/^"|"$/g, "");
  return result;
}
function parseHlsTracks(text, baseUrl) {
  if (!text.trimStart().startsWith("#EXTM3U")) throw new Error("The response is not an HLS playlist.");
  const lines = text.split(/\r?\n/).map(line => line.trim());
  const tracks = new Map();
  let master = false;
  function add(uri, role, attrs) {
    if (!uri || uri.includes("{$")) return;
    let url;
    try { url = new URL(uri, baseUrl); } catch { return; }
    if (!["https:", "http:"].includes(url.protocol)) return;
    const previous = tracks.get(url.href);
    if (previous?.role === "audio" && role !== "audio") return;
    tracks.set(url.href, {url:url.href, role, name:attrs.NAME || attrs.RESOLUTION || "", language:attrs.LANGUAGE || "", group:attrs["GROUP-ID"] || attrs.AUDIO || ""});
  }
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith("#EXT-X-MEDIA:")) {
      master = true;
      const attrs = hlsAttributes(line.slice(line.indexOf(":") + 1));
      if (attrs.TYPE === "AUDIO") add(attrs.URI, "audio", attrs);
    }
    if (line.startsWith("#EXT-X-STREAM-INF:")) {
      master = true;
      const attrs = hlsAttributes(line.slice(line.indexOf(":") + 1));
      const codecs = (attrs.CODECS || "").split(",").map(value => value.trim().toLowerCase()).filter(Boolean);
      const audioOnly = codecs.length > 0 && codecs.every(codec => /^(mp4a|ac-3|ec-3|opus|flac|alac)(\.|$)/.test(codec)) && !attrs.RESOLUTION;
      const hasVideo = !!attrs.RESOLUTION || codecs.some(codec => /^(avc[13]|hev1|hvc1|av01|vp09|vp9|dvh1|dvhe)(\.|$)/.test(codec));
      const hasAudio = codecs.some(codec => /^(mp4a|ac-3|ec-3|opus|flac|alac)(\.|$)/.test(codec));
      let next = i + 1;
      while (next < lines.length && !lines[next]) next++;
      if (lines[next] && !lines[next].startsWith("#")) add(lines[next], audioOnly ? "audio" : hasVideo && !hasAudio && !attrs.AUDIO ? "video" : "unknown", attrs);
    }
  }
  return {master, tracks:Array.from(tracks.values())};
}
