# Faaruun Hin Callisu

A film about an elderly mother in Dambi Doolloo and the song her son left behind. Narration is Afaan Oromo. Subtitles are English. The picture is a painted still, moved with a slow zoom, under an original instrumental score. Three clocks, and they are not the same number: the ten shot durations sum to 79 seconds; the radio cut is 82 seconds because it keeps those lengths and adds the 3-second end card; the picture exports are 90.042 seconds because each line is slowed to 0.88× and the frame holds to the voice, then the same 3-second card.

## The family page

A relative opens one page, answers three things, and gets a short vertical film. Nothing to install.

**https://faaruun.vercel.app**

Vercel hosts that page for free on the Hobby plan, and the deploy comes from this GitHub repository, not from a laptop. The project name is `faaruun`. The address `heritage-short.vercel.app` is a different film and is not this one. The hosted copy is a dry preview: flat frames, a quiet tone, no Addis call, no Cloudflare call. A real film, with her voice and the painted frames, is still `make family` on this machine. The keys stay in `.env`. Details are in `FAMILY.md`.

One command rebuilds it from the storyboard:

```bash
make film
```

That runs, in order: validate the storyboard, narrate, reference sheet, keyframes, moving shots, music log, assemble. A second run skips a reference sheet, a keyframe, or a shot whose inputs have not changed.

## What you need

- Python 3.12, `ffmpeg` and `ffprobe` on `PATH`
- A virtualenv with `jsonschema` and `addisai`

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Put keys in `.env`. The file is gitignored. Never commit it.

| Name | Used by |
| --- | --- |
| `ADDIS-AI-API-KEY` | Narration, Addis voice `om-ayyaantuu` |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | Reference sheet and keyframes, FLUX.2 klein 9B |
| `GEMINI_API_KEY` | Smoke tests only. The film voice is Addis, not Gemini |

`make film` is the whole pipeline. Narration, the reference portrait, and the first keyframes need the keys in `.env`. If `outputs/reference/golden_480.jpg` is already under 512 px, the reference step prints `cached` and does not call Cloudflare. If it is missing, that step generates `character.reference_seed` once and scales it. Music does not need a manual step: if `music_301.wav`, `music_302.wav`, `music_303.wav`, and `outputs/music/latencies.json` are already there, `make music` logs the Kaggle run and leaves the files alone. If they are missing, it writes a sine bed and logs that as ffmpeg. A shot with no keyframe copies the previous shot's clip and logs a hold. `outputs/` is gitignored, so a fresh clone does not contain the film. The first voice, the first portrait, and the first keyframes still come from the APIs.

## Stages

| Command | Reads | Writes |
| --- | --- | --- |
| `make validate` | `storyboard.json` | nothing, exit 0 or 1 |
| `make narration` | Oromo line and voice per shot | `outputs/narration/*.wav`, `timing.json` |
| `make radio` | narration | `outputs/radio_cut.mp4` (black picture, temp bed) |
| `make reference` | `character.reference_seed`, or the jpg already on disk | `outputs/reference/golden_480.jpg` |
| `make keyframes` | prompts, seeds, `outputs/reference/golden_480.jpg` | `outputs/keyframes/sNN_*.jpg` |
| `make shots` | keyframe plus `motion_prompt` | `outputs/shots/sNN_*.mp4` |
| `make music` | Kaggle wavs and latencies | `outputs/music/candidates.json`, lines in `runs.jsonl` |
| `make assemble` | shots, narration, seed 303 | `outputs/film_9x16.mp4`, `outputs/film_16x9.mp4` |

The contract is `storyboard.json`, validated against `schema/storyboard.schema.json` before every stage. Every model call appends one JSON line to `runs.jsonl`: model, parameters, seed, latency, cost, status.

## What it costs

Measured numbers are in `COSTS.md`. The film run stayed on free tiers. Addis list price for the ten lines in the cut is 5.82 ETB. Cloudflare stopped the tenth keyframe at the daily 10,000-neuron cap. No frontier video or music model was available.

`outputs/film_9x16.mp4` and `outputs/film_16x9.mp4` are the files for the film submission. Both are 90.042 seconds. They stay on disk and out of git: the vertical file is 95 MB, and the codebase grade does not open media. The evidence for each claim is in the logs and the markdown.

## Where to read next

`DESIGN.md` is the audience and the shot reasons. `ARCHITECTURE.md` is caching, retries, and what happens when a call fails. `EXPERIMENTS.md`, `FAILURES.md`, `COSTS.md`, and `ETHICS.md` are the evidence. `REPORT.md` is the write-up for assignment 1.

`python pipeline/benchmark_lang.py` speaks four storyboard fragments on Gemini TTS and on Addis, then counts token errors with Addis Scribe. It is not part of `make film`. E-011 is the result.
