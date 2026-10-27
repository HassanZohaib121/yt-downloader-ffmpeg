# Link Capture

A Windows desktop app that receives captured media sources from the Media Link Inspector Firefox extension and uses FFmpeg to save them.

## First-time setup

1. Extract the app bundle ZIP to a permanent folder. Keep the files together; Firefox’s bridge points to this folder.
2. Make sure `ffmpeg.exe` and `ffprobe.exe` are in `C:\ffmpeg\bin`. The app starts with that location selected. If yours differ, use the **FFmpeg Browse** button in the app.
3. In the extracted `link-capture-app` folder, right-click **Install-Firefox-Bridge.ps1** and choose **Run with PowerShell**. This registers the bridge for your Windows user and does not require administrator access.
4. In Firefox Developer Edition, open `about:debugging#/runtime/this-firefox`.
5. Click **Load Temporary Add-on**, select `firefox-extension/manifest.json` from the extracted bundle, and pin the extension to the toolbar if you like.
6. Start the app by opening **LinkCapture.exe**.

Temporary Firefox add-ons are removed when Firefox exits. After restarting Firefox, load the add-on again from `about:debugging`. The native bridge registration remains as long as you keep the extracted app folder in the same place.

## Capture and download

1. Open the media page in Firefox and press **Play**. Wait for its media requests to appear.
2. Click the extension icon and click **Open capture app** to send captured source options to the app. Or select a related video and audio pair in the extension and click **Send to app**.
3. In Link Capture, select a source from the inbox on the left.
4. Set the save folder, filename, and format. The filename starts with the captured page title; you can edit it. Changing the format updates the filename extension.
5. Click **Download**. Link Capture checks the source streams first, then shows download progress. Use **Cancel** to stop.
6. Click **Open folder** to view completed files.

The app supports **MKV, MP4, MOV, and WebM**. It copies the original audio and video codecs without re-encoding. MKV supports a wide range of codecs; if a format rejects a stream, try MKV. The app will not overwrite an existing output file. An interrupted or failed download may leave a partial file.

You can paste a direct media or playlist URL into **Add media URL**. A page URL, such as a YouTube watch link, is not itself a media source.

## Troubleshooting

- **The extension says it cannot open the app:** confirm you extracted the bundle, ran `Install-Firefox-Bridge.ps1`, and loaded `firefox-extension/manifest.json`. Keep the folder in place. Restart Firefox after installing the bridge.
- **No source appears:** reload the media page, press Play, wait briefly, then click **Open capture app** again.
- **The app reports no audio stream:** that source does not contain audio. Find a matching audio source from the same video and send the pair. Link Capture checks for audio before downloading.
- **The URL expired or returns an access error:** capture the media again and send the new link. Temporary media links can expire and may depend on browser session data that the app does not receive.
- **YouTube audio appears only as UMP/SABR requests:** those requests are diagnostic data, not standalone audio URLs. This app cannot extract audio from them.

The app stores captured URLs and preferences locally in its `data` folder. It does not send them to a remote service. FFmpeg is installed separately and is not bundled with the app.

## Remove the Firefox bridge

Run `Uninstall-Firefox-Bridge.ps1` from the extracted app folder. This removes the Firefox registration and keeps your captures and downloads. You can then delete the app folder yourself.

## Included files

- `LinkCapture.exe`: desktop app.
- `LinkCaptureHost.exe`: Firefox communication helper.
- `Install-Firefox-Bridge.ps1` and `Uninstall-Firefox-Bridge.ps1`: per-user bridge setup and removal.
- `firefox-extension/`: extension source to load in Firefox Developer Edition.
- `src/`: app and bridge source code.
