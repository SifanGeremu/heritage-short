# Architecture

Five stages share one contract, `storyboard.json`. Each stage reads that file and writes its own directory under `outputs/`. Nothing in a later stage reaches back into a provider. Assembly only sees files on disk.

```
storyboard.json
        │
        ▼
   validate.py          schema + shot ids unique + duration sum inside 60–90s
        │
        ├─ stage_narration.py   Addis om-ayyaantuu  →  outputs/narration/
        ├─ reference_sheet.py   seed on the board   →  outputs/reference/golden_480.jpg
        ├─ keyframes.py         FLUX.2 klein 9B     →  outputs/keyframes/
        ├─ shots.py             FFmpeg zoompan      →  outputs/shots/
        ├─ music.py             log Kaggle wavs     →  outputs/music/candidates.json
        └─ assemble.py          duck, subs, card    →  outputs/film_9x16.mp4
                                                         outputs/film_16x9.mp4
```

`make film` is that sequence, with the reference sheet between narration and keyframes. `pipeline/narration.py` and `pipeline/radio_cut.py` are thin entry points to the narration stage and the radio cut. When `golden_480.jpg` is already smaller than 512 px, the reference step does not call Cloudflare.

## Contract

The schema requires a `reason` on every shot, a duration, an image prompt, a motion prompt, and narration in Oromo and English. `validate.py` checks the schema, then checks invariants the schema does not: shot ids are unique, and the sum of shot `duration_s` is between 60 and 90. Music-cue durations are not added to that sum. The current board is ten shots. Those durations sum to 79 seconds, inside the 60–90 check. That sum is not the export length. The radio cut keeps each shot's `duration_s` and speeds a longer line to fit, then adds the 3-second end card, so it is 82.000 seconds. The picture exports slow each line to 0.88× and hold the frame to the voice, then add the same card, so both are 90.042 seconds, which is 90 seconds plus one frame at 24 fps.

Prompts, seeds, the voice, and `music.selected_seed` live in the storyboard, not in the stage scripts. Narration reads `tts.voice_name` and `project.narration_language` and does not replace them. The film's voice is `om-ayyaantuu` because that is the name in the storyboard. An empty `voice_name` stops the stage.

## Caching

A stage hashes the inputs that would change the output and stores the path in a `cache.json` next to the files.

| Stage | Key | Skip when |
| --- | --- | --- |
| Narration | text, voice, language, pad, fade | the wav for that hash is on disk |
| Keyframes | prompt, seed, reference image bytes | the jpg for that hash is on disk |
| Shots | keyframe bytes, move kind, frame count | the mp4 for that hash is on disk |

Change one Oromo line, run `make narration` then `make assemble`, and the other wavs are not resynthesized. Keyframes and shots do not move. `make shots` reads `motion_engine`. Every shot on this board says `ken_burns`: FFmpeg `zoompan` at 1080×1920, 24 fps, zoom never below 1, and the move comes from `motion_prompt` (push-in, pull-back, drift, or hold). `wan2.2` and `hunyuan1.5` are still understood, printed as "video model not called", and rendered with that same zoompan. Wan was not called. There is no Wan line in `runs.jsonl`. The cache key is the keyframe bytes and the move kind, not the engine name and not the whole motion sentence, so a wording change that stays in the same kind does not rebuild a clip. `character.reference_seed` is 201. `keyframes.py` reads it before any image call. The kept sheet is `outputs/reference/golden_480.jpg`.

## Retries

`common.with_retry` tries a call three times, sleeping 1s then 2s, and only on HTTP 429 and 503. A daily quota message (the body contains "daily", "per day", or "quota") is not retried. That is why the Cloudflare neuron cap stopped the run instead of hammering the endpoint. Addis is constructed with `max_retries=0` so the SDK does not retry behind this loop. Each attempt is one line in `runs.jsonl`.

## When a call fails

Keyframes save after every successful shot. A timeout on one shot leaves the earlier jpgs in place. The next `make keyframes` prints `cached` for those and tries only the missing shot. On 25 November the missing shot was s10: the read timed out at 145s, and the retry came back HTTP 429, daily free allocation of 10,000 neurons used up. s01–s09 stayed. Storyboard v3 put s10 back. It still has no keyframe of its own. `shots.py` copies the previous shot's clip, names the file from a hash of those bytes, and logs one line with `provider: ffmpeg` and `model: hold`. `python pipeline/shots.py --self-check` covers the copy in a temp directory. `make shots` wrote that hold as `outputs/shots/s10_886cac85.mp4` and logged it. The earlier hand file `outputs/shots/s10_hold9.mp4` is still on disk. Assemble uses the newest `s10_*.mp4`.

Assemble writes `outputs/assemble/stamp.json` after a successful export. The next `make assemble` skips the FFmpeg work when that digest matches the storyboard text plus the clip, narration, timing, and music bytes, and both exports are still on disk. There is no stamp yet, because assemble was not re-run after the check was added.

`make music` logs the Kaggle wavs when all three seeds and `latencies.json` are present, and does not rewrite them. If any of those files is missing, it writes a sine bed for each missing seed and logs `provider: ffmpeg`, `model: sine`. The s08 pluck time is the number in that shot's `music_cue` (`3.3s into`), read by both assemblers. It is not a hardcoded second path.

Assembly refuses to start if a shot has no clip, a narration wav is missing, or `music.selected_seed` has no wav. It does not substitute a silent bed.

## Picture and sound

The voice is one timeline: each line starts when the previous line ends, slowed to 0.88× with the pitch left alone. The score (seed 303) is trimmed to the picture, faded over the last 2 seconds, and ducked with `sidechaincompress` at threshold 0.02, ratio 6, attack 300 ms, release 1500 ms, after a fixed music gain of 0.32. Two-pass `loudnorm` targets −14 LUFS and a true peak of −1 dB. The measured input on the final mix was −17.31 LUFS.

English lines are burned in as ASS subtitles, chunked for a short line and a safe margin. The 9:16 export is 1080×1920. The 16:9 export is 1920×1080: the full portrait frame sits in the centre and a blurred cover of the same frame fills the sides, so heads and feet are not cropped. A drawn card reading "Made with AI" holds for 3 seconds.

## Secrets and logs

Keys are read from `.env` by name and redacted if a provider error would echo them. `runs.jsonl` stores prompts, seeds, latency, and cost. It does not store key values. `outputs/` is gitignored. The log is not.
