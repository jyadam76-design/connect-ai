# 도구 설치 상태 점검 (Windows)
Set-Location (Join-Path $PSScriptRoot "..")
$missing = $false
function Test-Tool($name, $cmd, $fix) {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) { Write-Host "  OK  $name" }
  else { Write-Host "  X   $name 없음 -> $fix"; $script:missing = $true }
}
Write-Host "영상 편집 도구 점검"
Test-Tool "FFmpeg"  "ffmpeg"  "winget install Gyan.FFmpeg"
Test-Tool "Whisper" "whisper" "py -m pip install --user openai-whisper"
Test-Tool "yt-dlp"  "yt-dlp"  "winget install yt-dlp.yt-dlp"
Test-Tool "Node"    "node"    "winget install OpenJS.NodeJS.LTS"
foreach ($p in "remotion","hyperframes") {
  if (Test-Path "작업중\motion\node_modules\$p") { Write-Host "  OK  $p" }
  else { Write-Host "  X   $p 없음 -> scripts\setup-windows.ps1 실행"; $missing = $true }
}
if ($missing) { exit 1 } else { Write-Host "모두 준비 완료" }
