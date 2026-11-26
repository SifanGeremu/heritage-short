# Failures

Defects found while smoke-testing Gemini speech for an Afaan Oromo line. An entry in `runs.jsonl` with `"status": "ok"` means the service returned audio. It does not mean the reading is correct.

## F-001. Afaan Oromo narration misreads the source sentence

| | |
| --- | --- |
| Status | Open |
| Severity | Blocker for narration use |
| Observed | 25 November 2026, 08:41:20 UTC |
| Component | `pipeline/smoke_gemini.py`, stage `tts` |
| Provider | Gemini |
| Model | `gemini-3.8-flash-tts` |
| Voice | Kore (prebuilt) |
| Artifact | `outputs/smoke/gemini-3.8-flash-tts.wav` |

### Summary

The speech request succeeded and produced a playable file. On listening review, the narration of the Afaan Oromo sentence is poor: words are spoken incorrectly. The clip cannot stand in for a faithful reading of the source text.

### Source text

```
Baga Nagaan Gara Addis Ai nagaan dhuftan!
```

The text was sent verbatim as the transcript. No style instruction, pronunciation lexicon, or language code was attached. The model was expected to read that sentence aloud.

### Conditions

- Endpoint: `generateContent` on `gemini-3.8-flash-tts`, chosen as the newest TTS model visible to the key.
- Voice configuration: `speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName = "Kore"`.
- Response: unary audio, reported as `audio/wav`.
- File on disk: mono, 16-bit PCM, 24 kHz, 69,120 frames, 2.88 seconds, 145,948 bytes.
- Log: `runs.jsonl` at `2026-11-25T08:41:20.516806+00:00`, stage `tts`, status `ok`, latency 3.269 seconds, cost 0.
- The same sentence, model, and voice had already been synthesized once, at `2026-11-25T08:40:11.875943+00:00`, also with status `ok`. The file above is the later take.

### Expected

A clear reading in which each word of the Afaan Oromo sentence can be recognized as the word that was written.

### Actual

The listener judged the narration poor. Words are rendered wrongly: the speech does not preserve the wording of the sentence. The failure is linguistic. The transport, the WAV container, and the API status all succeeded.

### Impact

The clip is not usable as Afaan Oromo narration. A greeting that mis-speaks its own words cannot be published, used as a sample, or treated as evidence that the model handles the language.

### Out of scope for this finding

The `text` stage against `gemini-3.8-flash` returned HTTP 503 ("high demand") on the same runs. That is an availability error on a different model and a different request. It did not prevent this file from being written, and it does not explain the misreading.

### Not yet established

Which words were substituted, and whether another prebuilt voice or an explicit language setting would change the reading, has not been measured. This record covers the Kore take of the sentence above on `gemini-3.8-flash-tts`.

## F-002. Radio cut v1 is not ready for audience testers

| | |
| --- | --- |
| Status | Fixed in storyboard v2 and radio cut v2 |
| Severity | Blocker for the first user test |
| Observed | 25 November 2026, listening review of `outputs/radio_cut.mp4` |
| Component | `pipeline/narration.py`, `pipeline/radio_cut.py` |
| Provider | Addis AI |
| Model | `om-bikila` |
| Artifact | `outputs/radio_cut.mp4` (v1, 75.000s) |

### Summary

Four defects showed up together on the v1 radio cut. The story was too thin, the voice was male, words were cut at clip edges, and several Afaan Oromo words were misread. v2 changes the script, the voice, the pad around each line, and the temp bed.

### Defects

1. Wrong TTS voice gender. The line `Ani weellistuu miti` is spoken by a woman, an elderly mother. v1 used Addis voice `om-bikila` and the reading was male.
2. Syllable clipping at clip boundaries. Heard fragments include `eegaa ja...`, `kuma qofa`, and `aggeeffadhu`, where the start or end of a word was cut off.
3. Afaan Oromo TTS mispronunciations. `Roobnis` was rendered as `Romnis`. `cuquliisaan` was rendered as `chukoliisaan`.
4. Eerie placeholder drone and a sparse script of about 45 words. Shots ran 6–11 seconds with little or no speech, so a listener who does not already know the story could not follow who the son was or what happened to him.

### Resolution

Storyboard v2 lengthens the narration and states a female delivery in `tts.style_instruction`. The voice that shipped is Addis `om-ayyaantuu`, not Gemini Aoede. Gemini TTS was already failing the language (F-001) and then returned HTTP 429 on the narration quota (F-005). Each generated wav is padded by 250ms in front and 350ms after, with a 15ms fade, and is not trimmed. The radio-cut bed is pink noise low-passed at 1200 Hz at −26 dB. Shot length in the cut is `max(storyboard duration, padded wav + 0.8s)`.

## F-003. Keyframe s10 stopped by a timeout, then the daily neuron cap

| | |
| --- | --- |
| Status | Closed by dropping s10. s01–s09 are the film |
| Severity | Blocks the last keyframe until the quota resets |
| Observed | 25 November 2026 |
| Component | `pipeline/keyframes.py` |
| Provider | Cloudflare Workers AI |
| Model | `@cf/black-forest-labs/flux-2-klein-9b` |
| Artifact | `outputs/keyframes/` (s01–s09). s10 was not written |

### Summary

The keyframe run got through nine shots. s10 timed out while the service was still working. A later retry did not generate it: the account had used the free allowance of 10,000 neurons for the day. The script kept the nine finished frames and stopped. The next `make keyframes` skips those nine and tries s10 again.

### Actual

s10's call (seed 110, no reference image) logged `status: error` after 145 seconds with `The read operation timed out`. The resume returned HTTP 429: "you have used up your daily free allocation of 10,000 neurons, please upgrade to Cloudflare's Workers Paid plan if you would like to continue usage." No s10 file was saved. s01–s09 stayed on disk and were reported as cached on the second run.

The storyboard no longer has s10. The closing beat is s09. A narration wav for the deleted shot is still on disk (`s10_3ad6d824.wav`) and is not in the edit.

## F-004. ACE-Step would not import on Kaggle

| | |
| --- | --- |
| Status | Fixed |
| Severity | Blocked the score until the process env was set |
| Observed | 25 November 2026, Kaggle notebook |
| Component | `notebooks/music_ace_step.py` |
| Provider | ACE-Step 1.5 |

Kaggle sets `MPLBACKEND` to `module://matplotlib_inline.backend_inline`. Inside the notebook's uv environment that backend is not a valid matplotlib value, and ACE-Step crashed on import with `ValueError`. The run was repeated with `MPLBACKEND=Agg`. Three instrumentals then completed in 1.701 GPU minutes. Seeds and latencies are in `outputs/music/latencies.json`.

## F-005. Gemini narration quota, and one Addis auth failure

| | |
| --- | --- |
| Status | Worked around. The film does not use Gemini audio. |
| Severity | Blocked the suggested TTS model |
| Observed | 25 November 2026 |
| Component | `pipeline/stage_narration.py`, `pipeline/smoke_addis.py` |

Fourteen `gemini-3.8-flash-tts` narration calls between 13:04 and 13:07 UTC returned HTTP 429, "You exceeded your current quota". No wav was written for those attempts. Earlier the same day, one Addis smoke call with `om-bikila` failed with `Authentication is required` (09:29 UTC) before the key was in place. Later Addis calls succeeded.

The workaround is the voice in the film: Addis `om-ayyaantuu`. Gemini stayed in the log as evidence that a 200, and then a 429, both failed to produce a usable Oromo line.

## F-006. Wan 2.2 was never run

| | |
| --- | --- |
| Status | Accepted fallback |
| Severity | The moving-shot stage is stills in motion, not generated video |
| Observed | Across `runs.jsonl`. No `wan` provider line. |
| Component | `pipeline/shots.py` |

The brief's video stage is Wan 2.2 image-to-video on Kaggle. This repo did not spend that GPU. After the keyframes existed, `shots.py` turned each jpg into a 24 fps clip with FFmpeg `zoompan`. Four shots in the storyboard still say `motion_engine: wan2.2`. The script does not read that field. It classifies `motion_prompt` into push-in, pull-back, drift, or hold.

This is the fallback the brief allows when video generation is not available. It is not a measured Wan failure. Wan was not given a chance to fail. The trade is recorded in EXPERIMENTS E-008: nine clips in 24 seconds of CPU, and no identity drift inside a clip, because the picture never leaves the keyframe.