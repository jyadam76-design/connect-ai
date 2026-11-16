#!/usr/bin/env python3
"""드라마 쇼츠 파이프라인 도구.

  tts     대본 → 나레이션 mp3 + 글자 단위 타이밍(ElevenLabs with-timestamps)
  subs    타이밍 → 자막(ASS) + 장면(문단)별 시작/끝 시간
  render  장면 이미지/영상 + 나레이션 + 자막 → 1080x1920 완성본

예)
  python3 pipeline.py tts    runs/ep001 --voice ksaI0TCD9BstzEzlxj4q
  python3 pipeline.py subs   runs/ep001
  python3 pipeline.py render runs/ep001 [--bgm bgm.mp3]

runs/epXXX/ 안에 필요한 파일:
  script.txt          빈 줄로 문단(=장면)을 나눈 확정 대본
  scenes/01.mp4|png…  장면 순서대로 (문단 수와 같게)
네트워크 키는 프록시가 넣어 주므로 xi-api-key 값은 더미입니다.
"""
import argparse, base64, json, os, re, subprocess, sys, urllib.request

W, H = 1080, 1920
FONT = os.environ.get("SUB_FONT", "Noto Sans CJK KR Black")  # 다른 환경에서는 SUB_FONT="Black Han Sans" 등


def paragraphs(run):
    txt = open(os.path.join(run, "script.txt"), encoding="utf-8").read().strip()
    return [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", txt) if p.strip()]


# ---------------------------------------------------------------- tts
def cmd_tts(a):
    text = "\n\n".join(paragraphs(a.run))
    body = json.dumps({
        "text": text, "model_id": a.model,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.3},
    }).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{a.voice}/with-timestamps?output_format=mp3_44100_128",
        data=body, headers={"xi-api-key": os.environ.get("XI_API_KEY", "dummy"), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    open(os.path.join(a.run, "narration.mp3"), "wb").write(base64.b64decode(d["audio_base64"]))
    al = d["alignment"]  # normalized_alignment는 한글을 로마자로 바꾸므로 원문 정렬을 쓴다
    json.dump({"text": text, **al}, open(os.path.join(a.run, "alignment.json"), "w"), ensure_ascii=False)
    print("narration.mp3", round(al["character_end_times_seconds"][-1], 2), "s")


# ---------------------------------------------------------------- subs
def ts(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    return f"{h}:{m:02d}:{t % 60:05.2f}"


def chunk_line(s, n=14):
    """한 화면 자막을 n자 안팎으로 끊는다(띄어쓰기 기준)."""
    out, cur = [], ""
    for w in s.split(" "):
        if cur and len(cur) + 1 + len(w) > n:
            out.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur: out.append(cur)
    if len(out) > 1 and len(out[-1]) <= 4:  # "원." 처럼 짧게 남은 꼬리는 앞줄에 붙인다
        tail = out.pop()
        out[-1] = f"{out[-1]} {tail}"
    return out


def cmd_subs(a):
    al = json.load(open(os.path.join(a.run, "alignment.json"), encoding="utf-8"))
    chars, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    full = "".join(chars)
    # 문단 경계(빈 줄) → 장면 시간
    scenes, i0 = [], 0
    for m in list(re.finditer(r"\n\s*\n", full)) + [None]:
        i1 = m.start() if m else len(full)
        seg = full[i0:i1]
        lead = len(seg) - len(seg.lstrip())
        a0, a1 = i0 + lead, i0 + len(seg.rstrip()) - 1
        if a1 >= a0:
            scenes.append({"start": st[a0], "end": en[a1], "text": seg.strip()})
        i0 = m.end() if m else i1
    for k in range(len(scenes) - 1):  # 장면 사이 공백은 앞 장면이 채운다
        scenes[k]["end"] = scenes[k + 1]["start"]
    scenes[0]["start"] = 0.0
    scenes[-1]["end"] = en[-1] + 0.6
    # 자막 줄: 문장부호/14자 단위
    events, pos = [], 0
    for sc in scenes:
        idx = full.find(sc["text"], pos); pos = idx + len(sc["text"])
        for sent in re.findall(r"[^.?!”]+[.?!”]*", sc["text"]):
            sent = sent.strip()
            if not sent: continue
            for line in chunk_line(sent):
                j = full.find(line, idx)
                if j < 0: continue
                events.append((st[j], en[j + len(line) - 1], line)); idx = j + len(line)
    for k in range(len(events) - 1):
        s0, e0, t0 = events[k]
        events[k] = (s0, max(e0, min(events[k + 1][0], e0 + 0.4)), t0)
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{FONT},86,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,7,2,2,60,60,560,1
Style: Hook,{FONT},96,&H0000E5FF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,8,2,8,60,60,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [f"Dialogue: 0,{ts(s)},{ts(e)},Sub,,0,0,0,,{t}" for s, e, t in events]
    hook = a.hook or ""
    if hook:
        lines.append(f"Dialogue: 1,{ts(0)},{ts(min(3.2, scenes[0]['end']))},Hook,,0,0,0,,{hook}")
    open(os.path.join(a.run, "subs.ass"), "w", encoding="utf-8").write(hdr + "\n".join(lines) + "\n")
    json.dump(scenes, open(os.path.join(a.run, "scenes.json"), "w"), ensure_ascii=False, indent=1)
    print(len(scenes), "scenes,", len(events), "subtitle lines")


# ---------------------------------------------------------------- render
def scene_file(run, n):
    for ext in ("mp4", "mov", "webm", "png", "jpg", "jpeg", "webp"):
        p = os.path.join(run, "scenes", f"{n:02d}.{ext}")
        if os.path.exists(p): return p
    sys.exit(f"장면 파일이 없습니다: scenes/{n:02d}.*")


def cmd_render(a):
    scenes = json.load(open(os.path.join(a.run, "scenes.json"), encoding="utf-8"))
    os.makedirs(os.path.join(a.run, "tmp"), exist_ok=True)
    parts = []
    for i, sc in enumerate(scenes, 1):
        src, dur = scene_file(a.run, i), sc["end"] - sc["start"]
        out = os.path.join(a.run, "tmp", f"p{i:02d}.mp4")
        fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
        if src.endswith((".png", ".jpg", ".jpeg", ".webp")):
            # 사진은 천천히 확대(켄 번스)해서 움직임을 준다
            frames = int(dur * 30) + 1
            zoom = "1+0.10*on/" + str(frames) if i % 2 else "1.10-0.10*on/" + str(frames)
            vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
                  f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=30,setsar=1")
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", src, "-vf", vf, "-t", f"{dur:.3f}"]
        else:
            # 영상이 짧으면 반복, 길면 자른다
            cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", src, "-vf", fit + ",fps=30",
                   "-t", f"{dur:.3f}", "-an"]
        subprocess.run(cmd + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", out], check=True)
        parts.append(out)
    lst = os.path.join(a.run, "tmp", "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(p)}'\n" for p in parts))
    silent = os.path.join(a.run, "tmp", "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent], check=True)
    ass = os.path.abspath(os.path.join(a.run, "subs.ass")).replace(":", r"\:")
    inputs = ["-i", silent, "-i", os.path.join(a.run, "narration.mp3")]
    if a.bgm:
        inputs += ["-stream_loop", "-1", "-i", a.bgm]
        af = "[2:a]volume=0.12[b];[1:a][b]amix=inputs=2:duration=first:dropout_transition=0[a]"
        amap = ["-filter_complex", af, "-map", "0:v", "-map", "[a]"]
    else:
        amap = ["-map", "0:v", "-map", "1:a"]
    final = os.path.join(a.run, "final.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-vf", f"ass='{ass}'" + (f":fontsdir='{os.path.abspath(a.fontsdir)}'" if a.fontsdir else ""), *amap,
                    "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", final], check=True)
    print(final)


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("tts"); t.add_argument("run"); t.add_argument("--voice", required=True)
    t.add_argument("--model", default="eleven_multilingual_v2")
    s = sp.add_parser("subs"); s.add_argument("run"); s.add_argument("--hook", default="")
    r = sp.add_parser("render"); r.add_argument("run"); r.add_argument("--bgm"); r.add_argument("--fontsdir")
    a = p.parse_args()
    {"tts": cmd_tts, "subs": cmd_subs, "render": cmd_render}[a.cmd](a)


if __name__ == "__main__":
    main()
