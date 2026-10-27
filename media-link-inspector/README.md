# Media Link Inspector for Firefox
1. Open about:debugging#/runtime/this-firefox in Firefox Developer Edition.
2. Click Load Temporary Add-on and select manifest.json in this folder.
3. Open a YouTube watch page, reload it, and press Play.
4. Click the extension in Firefox's Extensions menu (puzzle icon); pin it to the toolbar if desired.
5. Inspect or copy the captured URLs. Click Refresh to get newer requests.
6. Change playback quality to produce additional stream requests.

The badge counts unique URLs in the tab. Results clear on page loading, tab closure, extension reload, or browser restart. YouTube's in-page navigation may retain earlier results: use Clear and resume playback to isolate a video. Ads may also appear.

This is a passive request inspector, not a complete YouTube downloader. It captures response URLs via webRequest.onHeadersReceived and identifies audio/video MIME types, playlists, media requests, and googlevideo.com/videoplayback. It preserves exact URLs, including signed query parameters. Separate segment/range URLs remain separate. Repeated identical method+URL requests update the existing entry. At most 150 entries are retained per tab.

YouTube may deliver separate audio and video, expiring signed URLs, or POST requests requiring a body. A copied URL can therefore fail outside the original playback context. The extension does not capture request bodies or cookies, merge streams, or decrypt DRM. HTTP error responses are shown with their status.

Permissions: webRequest observes requests; all_urls allows detection across page and media CDN origins; tabs identifies the current tab; clipboardWrite supports the Copy URL button. Captured URLs stay in background memory and are not sent anywhere by this extension.

Firefox Manifest V2 is used for a simple persistent background script. This prototype is for temporary local installation, not yet packaged for Mozilla publication. Temporary extensions are removed when Firefox restarts.

Sources:
https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/webRequest
https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/webRequest/onHeadersReceived
https://extensionworkshop.com/documentation/develop/temporary-installation-in-firefox/
