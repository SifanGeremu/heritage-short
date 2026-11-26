# Experiments

Each entry is one change, checked against `runs.jsonl` or a file on disk. Ten are recorded. The listening choice between music seeds is the one result that is not in the log: the storyboard locks seed 303, and the log only has latency.

## E-001. Validation stops when a shot has no reason

Hypothesis: `make validate` accepts the storyboard, and deleting one `reason` fails on that field.

Change: Ran `make validate`. Removed `shots[0].reason` on s01, ran it again, restored the file.

Result: The intact board printed `ok` and exited 0. With `reason` removed, the validator printed `$.shots[0].reason: 'reason' is a required property` and exited 1. Restored, `make validate` passed again. The board at that moment still had s01–s10. It is nine shots now. See E-010.

## E-002. A successful Gemini TTS call is not an Afaan Oromo reading

Hypothesis: `gemini-3.8-flash-tts` with voice Kore will speak an Oromo sentence if the API returns audio.

Change: Smoke test, 25 November 2026, 08:41 UTC. Text sent verbatim: `Baga Nagaan Gara Addis Ai nagaan dhuftan!` No style line, no language code. Same call had already succeeded at 08:40 UTC.

Result: Status `ok`, latency 3.269 s, cost 0, file `outputs/smoke/gemini-3.8-flash-tts.wav` (mono, 16-bit, 24 kHz, 2.88 s). On listening, the words were not the words written. HTTP success was logged and the take was rejected. Detail in FAILURES F-001.

## E-003. Gemini 3.8 Flash text was down; Flash-Lite answered

Hypothesis: `gemini-3.8-flash` will answer a one-word smoke prompt.

Change: Fourteen text calls between 08:37 and 09:28 UTC on 25 November.

Result: Thirteen HTTP 503 ("high demand") and one read timeout. Zero `ok` lines for that model. Four calls to `gemini-3.5-flash-lite` in the same log all returned `ok` (42.4 s combined). The heavy model was not usable for drafting that morning. Later narration did not depend on it.

## E-004. The mother's voice cannot be om-bikila

Hypothesis: Addis `om-bikila` can narrate the mother.

Change: Nine narration calls on 25 November, all status `ok`, 53.4 s combined latency. Radio cut v1 assembled from those wavs.

Result: The voice read as male. The line `Ani weellistuu miti` is a woman speaking. Syllables were also clipped at the wav edges (`Roobnis` heard as `Romnis`). The voice and the pad both changed. See F-002. The final voice is `om-ayyaantuu`.

## E-005. om-ayyaantuu plus padding is the take in the film

Hypothesis: A female Addis voice, with silence kept on both ends of each wav, will survive a listen that om-bikila failed.

Change: Ten calls, voice `om-ayyaantuu`, language `om`, format `wav_44100`. Each file padded 250 ms / 350 ms and faded 15 ms. Logged cost is the Voices 2 list price, 5 ETB per minute.

Result: All ten status `ok`. Combined latency 88.9 s. Combined list price 5.12 ETB including a leftover s10 line. The nine lines in the cut (s01–s09) are 60.49 s of audio and 4.59 ETB. Those wavs are the ones `timing.json` points at for s01–s09, and they are the voice in `outputs/film_9x16.mp4`.

## E-006. Four reference seeds, one face kept

Hypothesis: Four FLUX.2 klein 9B portraits at seeds 201–204 will produce one face later shots can follow.

Change: `pipeline/reference_sheet.py`, 25 November 13:48–13:49 UTC. Same character prompt, seeds 201, 202, 203, 204. Latencies 13.1 s, 13.7 s, 15.0 s, 15.1 s. Cost 0.

Result: Seed 201 was kept as `outputs/reference/golden.jpg` and scaled to `golden_480.jpg`. The reason for that seed: she looks straight at us, calm, cream scarf, worn brown dress, and both hands in frame, so later shots have a face to follow. Character shots pass that image as the klein reference. Shots with `has_character: false` (s01) do not.

## E-007. Nine keyframes, then the neuron cap

Hypothesis: One klein 9B keyframe per shot, character shots conditioned on the golden reference, will finish a ten-shot board inside the free daily allowance.

Change: Seeds 101–109 for s01–s09, then seed 110 for s10. Image size 1080×1920.

Result: s01–s09 succeeded. Latencies 18.5, 16.8, 28.2, 20.7, 13.8, 14.2, 24.7, 16.6, 31.4 seconds (about 185 s combined). s10 timed out after 145 s with no file. A later call returned HTTP 429: daily free allocation of 10,000 neurons used up. Logged cost on every call was 0. The nine jpgs were cached. A rerun prints `cached` and does not regenerate them.

## E-008. Moving shots without Wan

Hypothesis: A slow FFmpeg zoom on the keyframe is enough motion for a narrated film, and it spends no Kaggle GPU.

Change: `pipeline/shots.py` maps `motion_prompt` to push-in, pull-back, drift, or hold, and renders 24 fps zoompan. Nine clips, 25 November. Combined FFmpeg latency 24.1 s. Cache key is the keyframe bytes plus the move.

Result: All nine status `ok`. No Wan line exists in `runs.jsonl`. The storyboard still says `motion_engine: wan2.2` on s01, s02, s06, and s07. That field is not read. Re-running `make shots` with the same jpgs and prompts hits the cache.

## E-009. Three ACE-Step seeds, one selected

Hypothesis: Three instrumental seeds at 68 BPM in A minor will give a bed that can sit under a voice. One of them gets locked in the storyboard.

Change: ACE-Step 1.5 on Kaggle, `MPLBACKEND=Agg` after the notebook crashed on Kaggle's inline matplotlib backend. Seeds 301, 302, 303. Captions are the two cues in the storyboard (sparse guitar, then a warmer resolve). `instrumental: true`.

Result: From `outputs/music/latencies.json` and `candidates.json`: 1.701 GPU minutes. Seed 301, 18.373 s, 84 s of audio. Seed 302, 13.288 s, 84 s. Seed 303, 13.302 s, 84 s. All three logged status `ok`, cost 0. `music.selected_seed` is 303, and `assemble.py` refuses to run if that wav is missing. The log does not record a listening vote. 303 is the seed in the film. 301 and 302 stay on disk as the rejected takes.

## E-010. Drop s10 rather than wait a day for one keyframe

Hypothesis: A nine-shot cut still lands inside 60–90 seconds and still carries the ending.

Change: s10 had narration (`s10_3ad6d824.wav`, 6.9 s, 0.525 ETB) and no picture. The shot was removed from `schema/storyboard.json`. The closing beat stayed on s09 (the close-up at the door).

Result: Shot durations now sum to 70 seconds. `make validate` accepts the board. The export is 72.5 seconds with the 3-second "Made with AI" card. The Amharic lines on each shot were never synthesized. `tts.languages_to_benchmark` lists `om` and `am`. Only `om` was spoken.
