$ErrorActionPreference = 'Stop'
$key = 'HKCU:\Software\Mozilla\NativeMessagingHosts\local.media_link_capture'
$expected = Join-Path $PSScriptRoot 'local.media_link_capture.json'
if (Test-Path -LiteralPath $key) {
  $value = (Get-Item -LiteralPath $key).GetValue('')
  if ($value -eq $expected) { Remove-Item -LiteralPath $key }
  else { throw 'The bridge points to another installation; no changes made.' }
}
Write-Output 'Firefox bridge unregistered. App files, captures, and downloads were preserved.'
