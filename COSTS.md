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
| Narration | Addis `om-ayyaantuu`, first female take, 10 ok | 89 s | 5.12 ETB for all 10 | 4.59 ETB for the nine lines in the 72.5 s export (60.49 s of audio). Replaced. |
| Narration | Addis `om-ayyaantuu`, 26 November retake, 10 ok | 141 s | 5.82 ETB | **5.82 ETB**, the ten lines in the film (`timing.json`, 75.89 s of audio) |
| Reference | klein 9B, seeds 201–204 | 57 s | 0 | Cloudflare free allowance |
| Keyframes | klein 9B, s01–s09 | 185 s | 0 | Same allowance. s10 never got an image. |
| Shots | FFmpeg zoompan, 9 clips | 24 s | 0 | Local CPU. No GPU. |
| Music | ACE-Step 1.5, seeds 301–303, Kaggle T4 | 1.701 GPU minutes; 44.963 s logged latency | 0 | $0.0149. Arithmetic below. |
| Assemble | One pass, 26 November 08:02–08:06 UTC | 316.435 s of FFmpeg | 0 | Local CPU. This is one of three passes. The log total is below. |
| Language probe | Gemini TTS, 4 short lines, all ok | 29.4 s | 0 | Free tier. Not in the film. E-011. |
| Language probe | Addis, 3× `om-ayyaantuu` and 1× `am-meron` | 37.4 s | 1.2884 ETB | 15.46 s of audio at 5 ETB per minute. Not in the film. |

## What the log adds up to

`runs.jsonl` has 175 lines. Summing `latency` and `cost` by stage:

| Stage | Lines | Latency (s) | Logged cost |
| --- | ---: | ---: | ---: |
| list | 7 | 8.396 | 0 |
| text | 18 | 280.557 | 0 |
| tts | 9 | 39.505 | 0.8483 ETB |
| narration | 56 | 474.657 | 12.7957 ETB |
| image | 1 | 12.943 | 0 |
| reference | 4 | 56.898 | 0 |
| keyframes | 22 | 385.695 | 0 |
| shots | 12 | 29.980 | 0 |
| music | 3 | 44.963 | 0 |
| assemble | 18 | 1011.373 | 0 |
| benchmark-tts | 8 | 66.833 | 1.2884 ETB |
| benchmark-scribe | 17 | 0 | 0 |

The narration 12.7957 ETB is the 10.94 ETB of `om-ayyaantuu` (5.12 + 5.82) plus 1.8557 ETB of `om-bikila`. The table above the fold splits those takes. It does not replace this sum.

The shots row is the nine zoompan clips plus the s10 hold logged on 26 November at 16:21 UTC: `outputs/shots/s10_886cac85.mp4`, `model: hold`, latency 0.011 s. The 24 s in the first table is the zoompan pass.

Assemble is three passes, not one. 25 November 21:00 UTC is 296.425 s. 26 November 08:00 UTC is 316.435 s. 26 November 11:00 UTC is 398.513 s. The row in the first table is the middle pass.

Seventeen `benchmark-scribe` lines have no timestamp and no latency. The logger omitted both. Those rows were not rewritten, and Scribe was not called again. `log_scribe` now writes `latency`. A later run will have it. This one does not.

## List price, including the free invoice

Logged cost stays 0 where the invoice was 0. The list price is what the same quantity costs in public.

Cloudflare Workers AI is $0.011 per 1,000 neurons, and the free allocation is 10,000 neurons a day ([Workers AI pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/)). The account used that allocation. The log does not give a neuron count per image, so the equivalent priced here is the allowance that ran out: 10,000 / 1,000 × 0.011 = **$0.11**.

The score ran on a Kaggle T4 (`notebooks/music_ace_step.py`). Kaggle did not bill it. A published on-demand price for one T4 is the AWS `g4dn.xlarge` in US East (N. Virginia), $0.526 per hour ([g4dn.xlarge](https://compute.info/vm/aws/g4dn-xlarge/), prices as of 26 November 2026). 1.701 / 60 × 0.526 = **$0.0149**.

An Amharic reading of the ten lines already on the board was not synthesized. `python pipeline/benchmark_lang.py --quote` prices it from the Oromo seconds in `timing.json` (75.89 s) and the character counts, at the same 5 ETB per minute. The quote is 40.88 seconds and **3.4065 ETB**. No Amharic audio was made for that number.

## The cap that actually hit

Cloudflare's free account stopped at **10,000 neurons per day**. The API said so, HTTP 429, after s01–s09 were saved: "you have used up your daily free allocation of 10,000 neurons". The brief's rough guide was 50–170 images a day. This account did not get a tenth keyframe. The number that bound the run was neurons, not a count of pictures.

Gemini TTS hit a different wall the same day: HTTP 429, "You exceeded your current quota", fourteen narration attempts, no audio. That is why the film voice is Addis.

## What a rerun costs

A cached shot does not call the provider again. Regenerating one Oromo line is one Addis call, about 0.5 ETB at this script's length, plus a local assemble (about five minutes of FFmpeg for both aspect ratios on this machine). Regenerating one keyframe is one Cloudflare image call, if the daily neurons are not already spent. Regenerating a moving shot is a few seconds of FFmpeg.

## GPU minutes

Only the music stage used a GPU. 1.701 minutes on Kaggle for three 84-second instrumentals. Keyframes and narration were hosted APIs. Shots and assembly were local FFmpeg.
