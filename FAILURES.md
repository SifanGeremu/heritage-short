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

### Later

E-011 did not repeat this greeting. It spoke four later sentences. Gemini returned audio for all four. Addis matched more of the tokens. The greeting in this finding is still the one that was rejected by ear.

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
| Status | Keyframe never generated. `shots.py` copies the previous clip, logs `model: hold`, and assemble uses the newest `s10_*.mp4`. See F-009. |
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

On 25 November, after E-010, s10 was taken off the board. A narration wav for that cut is still on disk (`s10_3ad6d824.wav`). On 26 November the listens put s10 back. It still has no keyframe of its own. The children-in-the-rain frame was never generated (F-009). `make shots` on 26 November at 16:21 UTC copied `s09_40a1aeca.mp4` to `outputs/shots/s10_886cac85.mp4` and logged `provider: ffmpeg`, `model: hold`, latency 0.011 s. `outputs/shots/s10_hold9.mp4` is the hand copy from before that function. Assemble uses the newest `s10_*.mp4`.

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

The brief's video stage is Wan 2.2 image-to-video on Kaggle. This repo did not spend that GPU. After the keyframes existed, `shots.py` turned each jpg into a 24 fps clip with FFmpeg `zoompan`. The storyboard now says `ken_burns` on every shot. `shots.py` still reads `motion_engine`. A shot that says `wan2.2` or `hunyuan1.5` prints that the video model was not called and renders the same zoom. Wan is still untested. There is no Wan line in `runs.jsonl`. The trade is E-008: nine clips in 24 seconds of CPU, and no identity drift inside a clip, because the picture never leaves the keyframe.

## F-007. Film subtitles dropped s10

| | |
| --- | --- |
| Status | Fixed in storyboard v3 |
| Severity | The closing line never reached the burned-in captions |
| Observed | 26 November 2026, `outputs/assemble/subs_16x9.ass` and `subs_9x16.ass` |
| Component | `pipeline/assemble.py` `caption_cues`, `storyboard.json` |

### Summary

The English listen ended on the one-second card "word you wrote." Caaltuu thought the file had frozen. The radio-cut captions from the earlier ten-shot board still had the rain and the last line. The film caption files did not.

### Cause

`timing.json` still listed `outputs/narration/s10_3ad6d824.wav`. The storyboard did not. E-010 had removed s10 after the keyframe quota failed, and `caption_cues` walks `board["shots"]` only. Nothing checked that every non-empty English line became a subtitle block, or that the last block finished before the 3-second end card. The assembler did not drop a shot that was on the board. It never saw s10.

### Fix

s10 is back on the board, 9 seconds, the answer to the proverb. Each dialogue line in the `.ass` file carries the shot id in the Name field. `assert_subtitle_coverage` refuses the cut unless the subtitle blocks are exactly the shots with English narration, in order, and s10's last cue ends at or before the end card.

## F-008. Subtitle cards split on a character window

| | |
| --- | --- |
| Status | Fixed |
| Severity | Listeners heard the track stop on a one-word card |
| Observed | 26 November 2026, the same `subs_16x9.ass` |
| Component | `pipeline/stage_assemble.py` `chunk_cues` |

### Summary

Boonaa named the cards out loud: "house, is gone." "weep." "in silence." "one note." Each was its own cue, about a second long. They are the tails of longer sentences, not lines anyone wrote.

### Cause

`chunk_cues` wrapped by pixel width, then took the lines two at a time. A sentence that needed five lines became two full cards and a leftover card of one or two words. `_hold_short_cues` only kept that leftover on screen longer. It did not put the words back on the sentence.

### Fix

The splitter breaks on `.` `?` `!` `—` `:` and `,` first, and an ellipsis is one break. A fragment of one or two words is glued to the neighbour clause. Each line is at most 40 characters and still has to fit the vertical safe area. A cue is at most two lines. The coverage check rejects a one- or two-word cue when the shot's full line is longer than that.

## F-009. Child-and-mother keyframes stopped on image quota

| | |
| --- | --- |
| Status | Open |
| Severity | Memory shots still show the room or the mother alone |
| Observed | 26 November 2026, 10:40 UTC |
| Component | `pipeline/keyframes.py` |
| Providers | Cloudflare FLUX.2 klein 9B, Gemini image, Pollinations flux |

### Summary

s01, s02, s03, s05, s09, and s10 now ask for the elderly mother together with a stylized painted child of about eight, and for neighborhood children where the line needs them. s04, s06, s07, and s08 stay the mother alone. None of the new frames were kept.

### Cause

Cloudflare returned HTTP 429: the daily free 10,000 neurons are spent. Every Gemini image model on the key returned HTTP 429 with a free-tier limit of 0. Pollinations flux at 768×1344 returned one jpeg for s01, then HTTP 402 Payment Required on the next request. `nologo=true` did not remove the pollinations.ai mark. The frame also drew a young woman, because Pollinations cannot take `golden_480.jpg` as a reference.

### What was kept

The jpeg is `outputs/smoke/s01_pollinations_mother_child.jpg`. It is not in `outputs/keyframes/` and not in the keyframe cache, so `shots.py` still uses the earlier FLUX frame. The next `make keyframes` after the Cloudflare day resets should draw the six shots with the reference mother.

## F-010. The video watch saw a black frame and the earlier lines

| | |
| --- | --- |
| Status | Fixed by reassembling the picture films on storyboard v3 |
| Severity | Viewers thought the video had not loaded, and they never heard his name |
| Observed | 26 November 2026, Girma, Geremew, and Amen |
| Component | `outputs/film_9x16.mp4`, `outputs/radio_cut.mp4` |

### Summary

Girma and Geremew saw a black frame and thought the phone was stuck. Girma: the screen stayed completely black, and when she said "Look" and "Listen" there was nothing to see or hear. Geremew heard her stop halfway through a word. Amen, reading the English, heard only rain when she plucked a string and said listen: no guitar, and no one singing. They also quoted "weep", a swallowed *hin jiru*, twisted *gitaara*, *Qubee*, *qalama cuquliisaan*, and *dhaloonni*, and said the film never spoke his name. Those lines are the 72-second picture export from before storyboard v3. The radio cut is black, and it already had the v3 lines. The guitar note started 1.5 seconds into s08, under the words, so they heard rain when she said listen. The full answers are in `DESIGN.md`, under the old-cut watch.

### Fix

`film_9x16.mp4` and `film_16x9.mp4` are cut again from the v3 narration and the existing frames. s10 reuses the s09 picture because that keyframe was never generated. The logged hold is `outputs/shots/s10_886cac85.mp4`. `s10_hold9.mp4` is the earlier hand copy. The pluck moves to 3.3 seconds, the gap in `s08_53ff8529.wav` after "Just one old string...", at gain 2.0, in both the radio cut and the picture mix.

## F-011. A fresh Addis take of the teaching sentence says baleessuu

| | |
| --- | --- |
| Status | Open. The film wav was not re-transcribed. |
| Severity | One word in s03 can reverse the meaning |
| Observed | 26 November 2026, E-011 |
| Component | `pipeline/benchmark_lang.py` |
| Provider | Addis |
| Model | `om-ayyaantuu`, scored by `scribe-turbo` |
| Artifact | `outputs/benchmark/om-qubee_addis.wav` |

The source slice is the second sentence of s03: `Ijoollee ollaa qubee—afaan keenyaan barreessuu—barsiistee, maqaa isaanii akka baratan goote.` Scribe wrote `baleessuu` where the line says `barreessuu`. Those are different words. Gemini's take of the same slice kept `barreessuu`. Scribe is not a listener. The film's own s03 wav is an earlier, longer take and was not the file transcribed here.