# 클로드 영상편집 도구 설치 (Windows). PowerShell에서 실행:
#   powershell -ExecutionPolicy Bypass -File scripts\setup-windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "▶ FFmpeg, yt-dlp, Node.js, Python (winget)"
winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
winget install -e --id yt-dlp.yt-dlp
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Python.Python.3.12

# 새로 설치한 도구를 이 창에서 바로 쓰도록 PATH 새로고침
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")

Write-Host "▶ Whisper (음성 → 자막)"
py -3.12 -m pip install --user -U openai-whisper

Write-Host "▶ Remotion + HyperFrames (작업중\motion)"
New-Item -ItemType Directory -Force "작업중\motion" | Out-Null
Push-Location "작업중\motion"
if (-not (Test-Path package.json)) { npm init -y | Out-Null }
npm install remotion @remotion/cli @remotion/captions react react-dom hyperframes
Pop-Location

& (Join-Path $PSScriptRoot "check.ps1")
