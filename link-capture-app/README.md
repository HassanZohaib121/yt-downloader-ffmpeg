# Link Capture
Windows desktop companion for Media Link Inspector.

## Start
Run LinkCapture.exe. FFmpeg and FFprobe are configured from C:\ffmpeg\bin; use Browse to change the path.

Install-Firefox-Bridge.ps1 registers this app for the current Windows user (no administrator rights required). Keep the app folder in place after registration, or run the installer again after moving it.

Reload the updated extension from its manifest.json in about:debugging. Click Open capture app to send captured sources, or choose a video/audio pair and click Send to app. The desktop app opens with the capture in its inbox. Choose a source, save folder, and filename, then Download.

You may also paste a direct HTTP(S) media/playlist URL. A YouTube watch-page URL is not a direct media URL.

## Behavior
- Uses argument arrays to launch FFmpeg; no shell commands or quote editing.
- Checks streams using FFprobe before downloading. Video/audio pairs require actual video in the first source and audio in the second. Single sources without audio are rejected to avoid silent video.
- Progress, logs, cancellation, output folder selection, and existing-video + audio merging.
- Existing output files are never overwritten. Cancelled/failed jobs may leave partial files.
- Captures and settings are stored locally under data/ next to the app. The inbox keeps the latest 100 capture batches.
- Only the configured Firefox extension ID can use the native messaging host. Browser messages only queue URLs and open the app; downloads require clicking Download.
- No server or listening network port.
- The extension is still temporarily installed and must be loaded again after restarting Firefox.
- Signed URLs expire. Browser-only session headers/cookies are not transferred.
- UMP/SABR extraction is not implemented. Adding the app does not create missing audio URLs.
- FFmpeg is installed separately and is not bundled.

## Remove
Run Uninstall-Firefox-Bridge.ps1 to remove this app's native messaging registration. Captures and downloads are preserved.

## Source
src/core.py: storage, URL validation, FFprobe and FFmpeg.
src/app.py: desktop UI.
src/native_host.py: Firefox native messaging.

## Filenames and formats
Captured video titles are used as filenames (Windows-invalid characters are replaced). Select MKV, MP4, MOV, or WebM beside the filename. Your format preference is saved when a download starts. Containers use the original codecs; choose MKV if another format rejects them. Pasted URLs without a title retain a generic editable name.

