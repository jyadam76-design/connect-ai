#!/usr/bin/env bash
# 클로드 영상편집 도구 설치 (macOS). 실행: bash scripts/setup-mac.sh
set -e
cd "$(dirname "$0")/.."

if ! command -v brew >/dev/null; then
  echo "▶ Homebrew 설치"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
fi

echo "▶ FFmpeg, yt-dlp, Node.js, Python"
brew install ffmpeg yt-dlp node python@3.12 pipx
pipx ensurepath

echo "▶ Whisper (음성 → 자막)"
pipx install openai-whisper || pipx upgrade openai-whisper

echo "▶ Remotion + HyperFrames 프로젝트 의존성 (작업중/motion)"
mkdir -p 작업중/motion
cd 작업중/motion
[ -f package.json ] || npm init -y >/dev/null
npm install remotion @remotion/cli @remotion/captions react react-dom hyperframes
cd ../..

bash scripts/check.sh
