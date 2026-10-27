# Using the YouTube captures
The popup now distinguishes HLS playlists, DASH manifests, YouTube UMP transport, and media responses.

An index.m3u8 file is a small playlist, not the video. The Copy FFmpeg command button on a successful GET HLS capture produces a PowerShell command that follows the playlist and remuxes its media to media-capture.mkv, without re-encoding. FFmpeg must be installed separately and available on PATH. Obtain it through https://ffmpeg.org/download.html. The extension does not execute commands or install software.

1. In about:debugging#/runtime/this-firefox, click Reload on Media Link Inspector.
2. Reload the YouTube video and start playback.
3. Open the extension popup and find an HLS playlist.
4. Click Copy FFmpeg command, then paste and run it in PowerShell in the folder where you want the output.
5. For a live playlist, press Q in FFmpeg to stop and finalize the file. Existing output files are not overwritten; rename the output in the command for another download.

Use a freshly captured playlist. A 403 response may require fresh session headers or tokens; the prototype does not transfer those. A playlist may be an advertisement or only one track. No live download has been verified using your particular captured URLs.

application/vnd.yt-ump is YouTube transport data. A URL copied from a POST request does not include its body or playback state, and changing it into a normal GET does not recreate the request. This extension labels those entries for diagnostics; it does not implement YouTube's UMP/SABR protocol.

One-click complete downloads would need a downloader implementation (for example a native helper connected through Firefox Native Messaging) that handles streams and combines audio/video. The present extension remains a request inspector with an HLS command helper.

https://ffmpeg.org/ffmpeg.html
https://github.com/yt-dlp/yt-dlp/issues/12482

## v0.3.0: combined video and audio commands
Reload the extension in about:debugging, reload the video, and open the popup.
Use Video + audio command at the top. Choose Download video and audio or Add audio to media-capture.mkv.
Select the video and audio sources, or paste an audio URL. Then copy the command and run it in PowerShell.
Unknown HLS/DASH playlists are not automatically paired: select sources from the same video. UMP/POST/error responses are excluded from the selectors. If audio is only available via UMP, this helper cannot produce a working audio source.
The command explicitly maps video from input 0 and audio from input 1, copies streams without re-encoding, and writes video-with-audio.mkv without overwriting existing files.
## v0.4.0: audio capture and playlist discovery
Direct audio responses are identified separately, including Googlevideo audio MIME hints.
Captured HLS playlists are inspected automatically (up to 12 per tab load) for EXT-X-MEDIA audio renditions and audio-only variants declared by CODECS. Relative URLs are resolved against the final playlist URL. Discovered references appear as Audio playlist, with track/language metadata where available, and are selectable for merging. A reference is not labeled as an HTTP success until its actual request is observed.
Click Find audio to retry inspection, then Refresh for automatic results. Each inspection has a 15-second timeout and a 2 MB limit. The extension fetches captured playlists using the browser session; it does not download their media segments. No additional permission is required.
Audio entries have a Copy audio-only command button, saving audio-capture.mka without re-encoding.
A media playlist that contains only video does not reveal a separate audio URL. UMP/SABR audio extraction is still unsupported. Discovery cannot invent a usable audio URL where the site provides none.
Reload in about:debugging and reload the video before testing.
## v0.5.0: one source dropdown
Video + audio now uses one dropdown of related source pairs. Choose one pair to generate the combined FFmpeg command. Pairs must share a parent playlist, reference that parent directly, or have the same Googlevideo media ID. Unknown playlists are never offered as audio; metadata-based pairing does not prove stream availability.
A checkbox switches to adding an identified audio source to the existing media-capture.mkv. The separate video/audio dropdowns and manual audio field have been removed.
Reload the extension and the video to capture fresh metadata.