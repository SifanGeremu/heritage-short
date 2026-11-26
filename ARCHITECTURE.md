# Architecture

Five stages share one contract, `schema/storyboard.json`. Each stage reads that file and writes its own directory under `outputs/`. Nothing in a later stage reaches back into a provider. Assembly only sees files on disk.

```
schema/storyboard.json
        │
        ▼
   validate.py          schema + shot ids unique + duration sum inside 60–90s
        │
        ├─ stage_narration.py   Addis om-ayyaantuu  →  outputs/narration/
        ├─ keyframes.py         FLUX.2 klein 9B     →  outputs/keyframes/
        ├─ shots.py             FFmpeg zoompan      →  outputs/shots/
        ├─ music.py             log Kaggle wavs     →  outputs/music/candidates.json
        └─ assemble.py          duck, subs, card    →  outputs/film_9x16.mp4
                                                         outputs/film_16x9.mp4
```

`make film` is that sequence. `pipeline/narration.py` and `pipeline/radio_cut.py` are thin entry points to the narration stage and the radio cut.

## Contract

The schema requires a `reason` on every shot, a duration, an image prompt, a motion prompt, and narration in Oromo and English. `validate.py` checks the schema, then checks invariants the schema does not: shot ids are unique, and the sum of shot `duration_s` is between 60 and 90. Music-cue durations are not added to that sum. The current board is nine shots, 70 seconds, plus a 3-second end card. The exported film is 72.5 seconds because lines overlap the crossfade and the voice sets the hold.

Prompts, seeds, the voice, and `music.selected_seed` live in the storyboard, not in the stage scripts. The narration script does hard-code the voice name `om-ayyaantuu` so a storyboard edit of `tts.voice_name` alone does not retake the audio. Change the constant in `pipeline/stage_narration.py` and the storyboard together.

## Caching

A stage hashes the inputs that would change the output and stores the path in a `cache.json` next to the files.

| Stage | Key | Skip when |
| --- | --- | --- |
| Narration | text, voice, language, pad, fade | the wav for that hash is on disk |
| Keyframes | prompt, seed, reference image bytes | the jpg for that hash is on disk |
| Shots | keyframe bytes, move kind, frame count | the mp4 for that hash is on disk |

Change one Oromo line, run `make narration` then `make assemble`, and the other eight wavs are not resynthesized. Keyframes and shots do not move. `make shots` never calls a video model. It classifies `motion_prompt` into push-in, pull-back, drift, or hold, and runs FFmpeg `zoompan` at 1080×1920, 24 fps, zoom never below 1. The storyboard field `motion_engine` still says `wan2.2` on four shots. The shots stage does not read that field. Wan 2.2 was not called. The pan-and-zoom is the fallback the brief allows when the video quota is not spent.

## Retries

`common.with_retry` tries a call three times, sleeping 1s then 2s, and only on HTTP 429 and 503. A daily quota message (the body contains "daily", "per day", or "quota") is not retried. That is why the Cloudflare neuron cap stopped the run instead of hammering the endpoint. Addis is constructed with `max_retries=0` so the SDK does not retry behind this loop. Each attempt is one line in `runs.jsonl`.

## When a call fails

Keyframes save after every successful shot. A timeout on one shot leaves the earlier jpgs in place. The next `make keyframes` prints `cached` for those and tries only the missing shot. On 25 November the missing shot was s10: the read timed out at 145s, and the retry came back HTTP 429, daily free allocation of 10,000 neurons used up. s01–s09 stayed. The storyboard was then cut to those nine shots.

Assembly refuses to start if a shot has no clip, a narration wav is missing, or `music.selected_seed` has no wav. It does not substitute a silent bed.

## Picture and sound

The voice is one timeline: each line starts when the previous line ends, slowed to 0.88× with the pitch left alone. The score (seed 303) is trimmed to the picture, faded over the last 2 seconds, and ducked with `sidechaincompress` at threshold 0.02, ratio 6, attack 300 ms, release 1500 ms, after a fixed music gain of 0.32. Two-pass `loudnorm` targets −14 LUFS and a true peak of −1 dB. The measured input on the final mix was −17.31 LUFS.

English lines are burned in as ASS subtitles, chunked for a short line and a safe margin. The 9:16 export is 1080×1920. The 16:9 export is 1920×1080: the full portrait frame sits in the centre and a blurred cover of the same frame fills the sides, so heads and feet are not cropped. A drawn card reading "Made with AI" holds for 3 seconds.

## Secrets and logs

Keys are read from `.env` by name and redacted if a provider error would echo them. `runs.jsonl` stores prompts, seeds, latency, and cost. It does not store key values. `outputs/` is gitignored. The log is not.
