# Costs

All figures are from `runs.jsonl`, `outputs/music/latencies.json`, and `outputs/narration/timing.json`. Logged `cost` is 0 on every free-tier call. Addis is the exception: the client writes the Voices 2 list price, 5 ETB per minute of audio, into the log. No frontier key (Omni, Nano Banana, Lyria) was available, so there is no side-by-side price against those models.

Measured on 25–26 November 2026.

## Per stage

| Stage | What ran | Measured time | Logged cost | List-price equivalent |
| --- | --- | --- | --- | --- |
| Text smoke | `gemini-3.8-flash`, 14 calls, all failed (503 or timeout) | 238 s latency | 0 | Free tier. The time was wasted waiting on a model that never answered. |
| Text smoke | `gemini-3.5-flash-lite`, 4 calls, all ok | 42 s | 0 | Free tier |
| TTS smoke | `gemini-3.8-flash-tts`, 7 ok | 30 s | 0 | Free tier. The wavs were not usable as Oromo. |
| Narration | Gemini TTS, 22 calls: 8 ok, 14 HTTP 429 quota | 96 s | 0 | Free tier, then the quota error. Not in the film. |
| Narration | Addis `om-bikila`, 9 ok (radio cut v1) | 53 s | list price in the log | Replaced. Male voice. |
| Narration | Addis `om-ayyaantuu`, 10 ok | 89 s | 5.12 ETB for all 10 | **4.59 ETB for s01–s09**, the lines in the film (60.49 s of audio) |
| Reference | klein 9B, seeds 201–204 | 57 s | 0 | Cloudflare free allowance |
| Keyframes | klein 9B, s01–s09 | 185 s | 0 | Same allowance. s10 never got an image. |
| Shots | FFmpeg zoompan, 9 clips | 24 s | 0 | Local CPU. No GPU. |
| Music | ACE-Step 1.5, seeds 301–303, Kaggle | 1.701 GPU minutes; 45 s of generation latency | 0 | Open weights. Kaggle's free GPU. |
| Assemble | Final pass, 26 November 08:02–08:06 UTC | 316 s of FFmpeg (picture, mix, two-pass loudnorm, both exports) | 0 | Local CPU |

## The cap that actually hit

Cloudflare's free account stopped at **10,000 neurons per day**. The API said so, HTTP 429, after s01–s09 were saved: "you have used up your daily free allocation of 10,000 neurons". The brief's rough guide was 50–170 images a day. This account did not get a tenth keyframe. The number that bound the run was neurons, not a count of pictures.

Gemini TTS hit a different wall the same day: HTTP 429, "You exceeded your current quota", fourteen narration attempts, no audio. That is why the film voice is Addis.

## What a rerun costs

A cached shot does not call the provider again. Regenerating one Oromo line is one Addis call, about 0.5 ETB at this script's length, plus a local assemble (about five minutes of FFmpeg for both aspect ratios on this machine). Regenerating one keyframe is one Cloudflare image call, if the daily neurons are not already spent. Regenerating a moving shot is a few seconds of FFmpeg.

## GPU minutes

Only the music stage used a GPU. 1.701 minutes on Kaggle for three 84-second instrumentals. Keyframes and narration were hosted APIs. Shots and assembly were local FFmpeg.
