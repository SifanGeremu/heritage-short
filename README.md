# Faaruun Hin Callisu

A film about an elderly mother in Dambi Doolloo and the song her son left behind. Narration is Afaan Oromo. Subtitles are English. The picture is a painted still, moved with a slow zoom, under an original instrumental score.

One command rebuilds it from the storyboard:

```bash
make film
```

That runs, in order: validate, narration, reference sheet, keyframes, shots, music, assemble. A second run skips a reference sheet, a keyframe, or a shot whose inputs have not changed.

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

`outputs/` is gitignored, so a fresh clone has no film. The first voice, the first portrait, and the first keyframes come from the APIs.

If `outputs/reference/golden_480.jpg` is already under 512 px, the reference step prints `cached` and does not call Cloudflare. If it is missing, that step generates `character.reference_seed` (201) once and scales it. If `music_301.wav`, `music_302.wav`, `music_303.wav`, and `outputs/music/latencies.json` are already there, `make music` logs the Kaggle run and leaves the files alone. If any of them is missing, it writes a sine bed and logs that as ffmpeg. That sine is not the score in the submitted film. The submitted score is seed 303. A shot with no keyframe copies the previous shot's clip and logs a hold. s10 is that hold: `outputs/shots/s10_886cac85.mp4`.

## Three clocks

The ten shot durations in `storyboard.json` sum to 79 seconds. That sum is what `make validate` checks, inside 60–90. It is not the length of either export.

`outputs/radio_cut.mp4` keeps those shot lengths, speeds a longer line to fit, and adds the 3-second end card, so it is 82.000 seconds. `make radio` builds that file. `make film` does not.

`outputs/film_9x16.mp4` and `outputs/film_16x9.mp4` are 90.042 seconds. Each line is slowed to 0.88× and the frame holds to the voice, then the same 3-second card. Both stay on disk and out of git. The codebase grade does not open media.

## Stages

| Command | Reads | Writes |
| --- | --- | --- |
| `make validate` | `storyboard.json` | nothing, exit 0 or 1 |
| `make narration` | Oromo line and voice per shot | `outputs/narration/*.wav`, `timing.json` |
| `make radio` | narration | `outputs/radio_cut.mp4` |
| `make reference` | `character.reference_seed`, or the jpg already on disk | `outputs/reference/golden_480.jpg` |
| `make keyframes` | prompts, seeds, `outputs/reference/golden_480.jpg` | `outputs/keyframes/sNN_*.jpg` |
| `make shots` | keyframe plus the move in `motion_prompt` | `outputs/shots/sNN_*.mp4` |
| `make music` | Kaggle wavs and latencies, or a sine if those files are missing | `outputs/music/candidates.json`, lines in `runs.jsonl` |
| `make assemble` | shots, narration, seed 303 | `outputs/film_9x16.mp4`, `outputs/film_16x9.mp4` |

The contract is `storyboard.json`, validated against `schema/storyboard.schema.json` before every stage. Prompts, seeds, the voice, and `music.selected_seed` live in that file. Every model call appends one JSON line to `runs.jsonl`: model, parameters, seed, latency, cost, status. Caching, the retry rule, and what a failed call leaves on disk are in `ARCHITECTURE.md`.

## What it costs

Measured numbers are in `COSTS.md`. The film run stayed on free tiers. Addis list price for the ten lines in the cut is 5.82 ETB. Cloudflare stopped the tenth keyframe at the daily 10,000-neuron cap. No frontier video or music model was available.

## The page

A relative can open one page, with nothing to install, and answer three things: a name and a first sentence, one object, and a last line. A short vertical film comes back. The last card says Made with AI.

**https://heritage-short-beta.vercel.app/**

Vercel hosts that page for free, from this repository. It is a public preview: flat frames and a quiet tone. It does not call Addis and it does not call Cloudflare, so a visitor cannot spend the keys. The keys stay in `.env`. A real film from those three answers, with her voice and the painted frames, is `make family` on this machine. That path does not read or write `storyboard.json`, and it does not write `outputs/film_9x16.mp4`. Details are in `FAMILY.md`.

The ten-shot film above is the submission. This page is not that film.

## Where to read next

`DESIGN.md` is the audience and the shot reasons. `ARCHITECTURE.md` is the contract, the cache, and what a failed call does. `EXPERIMENTS.md`, `FAILURES.md`, `COSTS.md`, and `ETHICS.md` are the evidence. `REPORT.md` is the write-up for assignment 1.

`python pipeline/benchmark_lang.py` speaks four storyboard fragments on Gemini TTS and on Addis, then counts token errors with Addis Scribe. It is not part of `make film`. E-011 is the result.
