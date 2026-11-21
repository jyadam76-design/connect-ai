#!/usr/bin/env bash
# 도구 설치 상태 점검 (macOS/Linux)
cd "$(dirname "$0")/.."
ok(){ printf "  ✅ %-12s %s\n" "$1" "$2"; }
no(){ printf "  ❌ %-12s 없음 → %s\n" "$1" "$2"; MISSING=1; }
echo "영상 편집 도구 점검"
command -v ffmpeg  >/dev/null && ok FFmpeg  "$(ffmpeg -version | head -1 | cut -d' ' -f3)" || no FFmpeg "brew install ffmpeg"
command -v whisper >/dev/null && ok Whisper "설치됨" || no Whisper "pipx install openai-whisper"
command -v yt-dlp  >/dev/null && ok yt-dlp  "$(yt-dlp --version)" || no yt-dlp "brew install yt-dlp"
command -v node    >/dev/null && ok Node    "$(node -v)" || no Node "brew install node"
[ -d 작업중/motion/node_modules/remotion ]    && ok Remotion    "설치됨" || no Remotion    "bash scripts/setup-mac.sh"
[ -d 작업중/motion/node_modules/hyperframes ] && ok HyperFrames "설치됨" || no HyperFrames "bash scripts/setup-mac.sh"
[ -z "$MISSING" ] && echo "모두 준비 완료 🎬" || exit 1
