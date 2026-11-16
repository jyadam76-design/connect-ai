# 드라마 쇼츠 자동화

시니어·드라마 쇼츠를 **주제 선정부터 예약 발행, 댓글 자동 DM까지** 만드는 파이프라인입니다.
사람은 대시보드에서 단계마다 체크만 하고, 나머지는 Claude가 [WORKER.md](WORKER.md)대로 처리합니다.

```
주제 레이더 → 레퍼런스 분석 → 대본 → 목소리 → 장면(사진/AI영상) → 편집본 → 썸네일 → 예약 발행 + 댓글 DM
  vidIQ        vidIQ 자막       Claude   ElevenLabs   Higgsfield         ffmpeg     Higgsfield   Uplika
```

| 폴더/파일 | 내용 |
|---|---|
| `dashboard/index.html` | 승인 대시보드 (claude.ai Artifact로 게시, DB 사용) |
| `WORKER.md` | Claude가 체크된 단계를 처리하는 규칙 |
| `scripts/pipeline.py` | 나레이션(TTS+타이밍) → 자막(ASS) → 1080×1920 합성 |
| `runs/epXXX/` | 에피소드별 작업 파일 (용량 큰 결과물은 커밋하지 않음) |

## 편집 도구 단독 사용

```bash
python3 scripts/pipeline.py tts    runs/ep001 --voice ksaI0TCD9BstzEzlxj4q   # script.txt → narration.mp3, alignment.json
python3 scripts/pipeline.py subs   runs/ep001 --hook "영수증을 꺼낸 며느리"  # → subs.ass, scenes.json
python3 scripts/pipeline.py render runs/ep001 [--bgm bgm.mp3]               # scenes/01.png|mp4 … → final.mp4
```

필요: ffmpeg(libass), `Noto Sans CJK KR` 글꼴, ElevenLabs 키(클라우드 세션에서는 프록시가 넣어 줌).

## 댓글 → DM 제약 (Meta 규칙)
- 인스타그램·페이스북만 가능합니다. 스레드·유튜브·틱톡은 DM 자동화가 없습니다.
- 댓글 1개당 비공개 답장 1번, 댓글이 달린 지 7일 안에만 보낼 수 있습니다.
- 팔로워 여부 확인은 인스타그램만 됩니다.
