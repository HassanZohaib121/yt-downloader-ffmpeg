$ErrorActionPreference = 'Stop'
$manifest = Join-Path $PSScriptRoot 'local.media_link_capture.json'
$hostExe = Join-Path $PSScriptRoot 'LinkCaptureHost.exe'
if (-not (Test-Path -LiteralPath $hostExe)) { throw 'LinkCaptureHost.exe is missing.' }
$config = @{
  name = 'local.media_link_capture'
  description = 'Send captured media links to Link Capture'
  path = $hostExe
  type = 'stdio'
  allowed_extensions = @('media-link-inspector@local.example')
}
[System.IO.File]::WriteAllText($manifest, ($config | ConvertTo-Json -Depth 4), (New-Object System.Text.UTF8Encoding($false)))
$key = 'HKCU:\Software\Mozilla\NativeMessagingHosts\local.media_link_capture'
New-Item -Path $key -Force | Out-Null
Set-Item -Path $key -Value $manifest
Write-Output 'Firefox bridge installed for the current Windows user. Reload the extension, then click Open capture app.'
