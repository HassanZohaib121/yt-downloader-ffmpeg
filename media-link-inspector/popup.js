"use strict";
let tabId;
const status = document.getElementById("status");
const results = document.getElementById("results");
function textBlock(text) {
  const p = document.createElement("p");
  p.textContent = text;
  return p;
}
function copyControl(text, label, ariaLabel) {
  const group = document.createElement("div");
  const field = document.createElement("textarea");
  field.readOnly = true;
  field.value = text;
  field.setAttribute("aria-label", ariaLabel);
  const button = document.createElement("button");
  button.textContent = label;
  button.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(text); button.textContent = "Copied"; }
    catch { field.focus(); field.select(); status.textContent = "Copy failed. Text is selected; press Ctrl+C."; }
  });
  group.append(field, button);
  return group;
}
async function render(type = "list") {
  try {
    if (!Number.isInteger(tabId)) throw new Error("No active tab available.");
    if (type === "discoverAudio") status.textContent = "Inspecting playlists for audio tracks…";
    const rows = await browser.runtime.sendMessage({type, tabId});
    rows.sort((a,b) => Number(describeMedia(b).type === "hls") - Number(describeMedia(a).type === "hls"));
    results.replaceChildren(renderMergeBuilder(rows));
    status.textContent = rows.length ? "Select a video + audio option below." : "No media yet. Reload the page and press Play, then click Refresh.";
  } catch (error) { status.textContent = error.message; }
}
document.getElementById("refresh").addEventListener("click", () => render());
document.getElementById("clear").addEventListener("click", () => render("clear"));
(async () => {
  try {
    const [tab] = await browser.tabs.query({active:true,currentWindow:true});
    tabId = tab?.id;
    await render();
  } catch (error) { status.textContent = error.message; }
})();


function renderMergeBuilder(rows) {
  const section = document.createElement("article");
  const heading = document.createElement("h2");
  heading.textContent = "Video + audio";
  section.append(heading);
  const existingLabel = document.createElement("label");
  const existing = document.createElement("input");
  existing.type = "checkbox";
  existingLabel.append(existing, document.createTextNode(" Use my downloaded media-capture.mkv"));
  section.append(existingLabel);
  const label = document.createElement("label");
  label.style.display = "block";
  label.style.marginTop = "12px";
  label.append(document.createTextNode("Select video + audio"));
  const select = document.createElement("select");
  select.style.width = "100%";
  select.style.marginTop = "5px";
  label.append(select); section.append(label);
  const info = textBlock("");
  const output = document.createElement("div");
  section.append(info,output);
  let options = [];
  function showCommand() {
    output.replaceChildren();
    if (select.value === "") return;
    const pair = options[Number(select.value)];
    if (!pair) return;
    try {
      const command = makeMergeCommand(pair.video?.url || "",pair.audio.url,existing.checked);

      const send = document.createElement("button");
      send.textContent = "Send to app";
      send.addEventListener("click", async () => {
        send.disabled = true;
        try {
          await sendCaptureToApp([{kind:existing.checked ? "existing" : "pair",
            ...(existing.checked ? {} : {video:pair.video.url}),audio:pair.audio.url,label:pair.label}]);
        } catch (error) {
          status.textContent = "Cannot send to app: " + error.message + " Run Install-Firefox-Bridge.ps1 once if needed.";
        } finally { send.disabled = false; }
      });
      output.append(send);

      output.append(copyControl(command,"Copy video + audio command","Combined FFmpeg command for PowerShell"));
      if (pair.video && mediaRole(pair.video) === "unknown") output.append(textBlock("The selected master/variant playlist is related to the audio, but its video track has not been probed."));
      output.append(textBlock("Run in PowerShell. Output: video-with-audio.mkv. Track availability is based on capture metadata; FFmpeg will verify the streams."));
    } catch (error) { output.append(textBlock(error.message)); }
  }
  function populate() {
    options = combinedSourceOptions(rows,existing.checked);
    select.replaceChildren();
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = options.length ? "Choose a video + audio option" : "No matching audio source found";
    select.append(placeholder);
    options.forEach((pair,index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = (index + 1) + ". " + pair.label;
      select.append(option);
    });
    select.disabled = !options.length;
    info.textContent = options.length ? existing.checked ? "Choose audio to add to media-capture.mkv in your current folder." : "Pairs share a playlist or YouTube media ID. Only identified audio sources are included." : "Click Find audio, then Refresh. Unknown playlists and UMP requests are not treated as audio.";
    showCommand();
  }
  existing.addEventListener("change",populate);
  select.addEventListener("change",showCommand);
  populate();
  return section;
}

document.getElementById("find-audio").addEventListener("click", async (event) => { 
  const button = event.currentTarget; button.disabled = true; try { await render("discoverAudio"); } finally { button.disabled = false; } });
async function sendCaptureToApp(choices) {
  const tab = await browser.tabs.get(tabId);
  const response = await browser.runtime.sendNativeMessage("local.media_link_capture", {
    action:"capture", title:tab.title || "Browser capture", choices:choices.slice(0,100)
  });
  if (!response?.ok) throw new Error(response?.error || "The desktop app did not respond.");
  status.textContent = "Sent to Link Capture. Choose your save location and click Download in the app.";
}
document.getElementById("open-app").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  try {
    const rows = await browser.runtime.sendMessage({type:"list",tabId});
    const pairs = combinedSourceOptions(rows).slice(0,60).map(pair => ({
      kind:"pair",video:pair.video.url,audio:pair.audio.url,label:pair.label
    }));
    const singles = rows.filter(selectableMedia).map(row => ({
      kind:"single",video:row.url,label:sourceLabel(row)
    }));
    await sendCaptureToApp([...pairs,...singles]);
  } catch (error) {
    status.textContent = "Cannot open Link Capture: " + error.message + " Run Install-Firefox-Bridge.ps1 once if the app is not registered.";
  } finally { button.disabled = false; }
});
