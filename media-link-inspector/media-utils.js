"use strict";
function describeMedia(row) {
  let path = "";
  try {
    path = new URL(row.url).pathname;
  } catch {}
  const mime = (row.mime || "").toLowerCase();
  if (mime === "application/vnd.yt-ump")
    return {
      type: "ump",
      title: "YouTube UMP transport",
      note: "This is a structured YouTube streaming response, not a standalone video file. Its POST body and playback state are needed; opening the URL as GET will not reproduce it.",
    };
  if (/mpegurl/.test(mime) || /\.m3u8$/i.test(path))
    return {
      type: "hls",
      title: row.role === "audio" ? "Audio playlist" : row.role === "video" ? "Video playlist" : "HLS playlist",
      note: "This small text file lists media segments or other playlists. Use an HLS downloader to fetch the media; saving the URL alone saves only the playlist.",
    };
  if (/dash\+xml/.test(mime) || /\.mpd$/i.test(path))
    return {
      type: "dash",
      title: "DASH manifest",
      note: "This is a manifest describing separate media streams, not a complete video file.",
    };
  return {
    type: "media",
    title: row.kind || "Media",
    note: row.range
      ? "This response contains only a byte range. The captured URL may represent a partial stream."
      : "This may be an audio track, video track, or segment rather than the complete video.",
  };
}
function makeHlsCommand(row) {
  if (
    describeMedia(row).type !== "hls" ||
    row.method !== "GET" ||
    row.status < 200 ||
    row.status >= 300
  )
    return null;
  if (
    !/^https?:\/\//i.test(row.url) ||
    /[\r\n\u2018\u2019\u201a\u201b]/.test(row.url)
  )
    return null;
  const quoted = quotePowerShell(row.url);
  return "ffmpeg -n -i " + quoted + ' -c copy "media-capture.mkv"';
}

function quotePowerShell(value) {
  if (/[\r\n\u0000]/.test(value)) throw new Error("URLs must be on one line.");
  return '"' + value.replace(/[`$"]/g, character => "`" + character) + '"';
}
function validMediaUrl(value) {
  const url = new URL(value);
  if (!["https:", "http:"].includes(url.protocol)) throw new Error("Use an HTTP or HTTPS media URL.");
  return value;
}
function selectableMedia(row) {
  return row.method === "GET" && ((row.status >= 200 && row.status < 300) || (row.discovered && row.status === null)) && describeMedia(row).type !== "ump";
}
function makeMergeCommand(videoUrl, audioUrl, existingVideo = false) {
  const audio = quotePowerShell(validMediaUrl(audioUrl));
  const video = existingVideo ? quotePowerShell("media-capture.mkv") : quotePowerShell(validMediaUrl(videoUrl));
  return "ffmpeg -n -i " + video + " -i " + audio + ' -map 0:v:0 -map 1:a:0 -c copy "video-with-audio.mkv"';
}

function mediaRole(row) {
  if (row.role && row.role !== "unknown") return row.role;
  if (describeMedia(row).type === "media" && row.mime?.startsWith("audio/")) return "audio";
  if (describeMedia(row).type === "media" && row.mime?.startsWith("video/")) return "video";
  return "unknown";
}
function makeAudioCommand(row) {
  if (mediaRole(row) !== "audio" || !selectableMedia(row)) return null;
  return "ffmpeg -n -i " + quotePowerShell(validMediaUrl(row.url)) + ' -map 0:a:0 -vn -c copy "audio-capture.mka"';
}

function youtubeMediaId(row) {
  try {
    const url = new URL(row.url);
    if (!(url.hostname === "googlevideo.com" || url.hostname.endsWith(".googlevideo.com"))) return null;
    return url.searchParams.get("id") || url.pathname.match(/\/id\/([^/]+)/)?.[1] || null;
  } catch { return null; }
}
function matchingSources(video, audio) {
  if (video.url === audio.url) return false;
  if (video.parentUrl && video.parentUrl === audio.parentUrl) {
    return !(video.group && audio.group && video.group !== audio.group);
  }
  if (video.url === audio.parentUrl) return true;
  const id = youtubeMediaId(video);
  return !!id && id === youtubeMediaId(audio);
}
function sourceLabel(row) {
  let itag = row.itag;
  try { itag ||= new URL(row.url).pathname.match(/\/itag\/([^/]+)/)?.[1]; } catch {}
  return [row.trackName || (mediaRole(row) === "audio" ? "Audio" : mediaRole(row) === "video" ? "Video" : "Playlist"),row.language,itag ? "itag " + itag : ""].filter(Boolean).join(" · ");
}
function combinedSourceOptions(rows, existing=false) {
  const sources = rows.filter(selectableMedia);
  const audioRows = sources.filter(row => mediaRole(row) === "audio");
  if (existing) return audioRows.map(audio => ({audio,video:null,label:"media-capture.mkv + " + sourceLabel(audio)}));
  const videos = sources.filter(row => mediaRole(row) === "video" || (mediaRole(row) === "unknown" && ["hls","dash"].includes(describeMedia(row).type)));
  const pairs = [];
  for (const video of videos) for (const audio of audioRows) {
    if (!matchingSources(video,audio)) continue;
    pairs.push({video,audio,label:sourceLabel(video) + " + " + sourceLabel(audio)});
    if (pairs.length >= 200) return pairs;
  }
  return pairs;
}
