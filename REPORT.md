# Report — Faaruun Hin Callisu

Assignment 1, AI-Content Generation. The repository is the pipeline. This note is what I set out to make, what the runs taught me, and what I have not earned yet.

## What I set out to make, and for whom

A film of about one minute for Oromo youth and the diaspora, and for families from Dembi Dollo and Wallaga, watched first on a phone. The feeling at the end was fixed before any image call: grief turning into pride. A mother in a rain-lit room touches her son's guitar, and a generation that did not know him still sings.

The film is *Faaruun Hin Callisu*. Nine shots, Afaan Oromo narration, English subtitles, an instrumental score, both aspect ratios, and a card that says it was made with AI. `outputs/film_9x16.mp4` and `outputs/film_16x9.mp4` are 72.5 seconds. `make film` is the command. The contract is `schema/storyboard.json`.

## What I learned from listening

The first radio cut was not ready for anyone else. It is FAILURES F-002. About 45 words, a male voice (`om-bikila`) saying a woman's line, words cut off at the edges of the wav (`Roobnis` heard as `Romnis`), and a drone that made the silence feel like a horror sting. A listener who did not already know the story could not have said who the son was.

That listen changed the storyboard. The narration now carries the guitar, Qubee, the cassette, the notebook, the line he left her, and August 1996. The voice is Addis `om-ayyaantuu`. Each line is padded instead of trimmed. Shot s03 shows the book and the chalk, not only the guitar.

Two tests with three people from the audience are not in `DESIGN.md`. I will not write quotes I do not have. Those notes go in after the cuts are actually played, and this report should be updated with what they said and which line moved. Until then the audience evidence is one serious listening pass and the diff it caused.

## The hardest problem

Gemini 3.8 Flash TTS is the model the brief points at, including for languages beyond English. It returned a valid wav for an Oromo greeting and the words were wrong (F-001, `runs.jsonl` status `ok`, latency 3.269 s, cost 0). I then hit HTTP 429 on the narration quota, fourteen times, and got no audio at all (F-005). A green log line was not a reading. A quota error was not a pronunciation problem. They felt the same from the outside: I still had no voice.

The fix was a provider that has Oromo voices, Addis, and a voice whose gender matches the speaker. `om-ayyaantuu` is the take in the film. Ten calls, all `ok`, 4.59 ETB of list price for the nine lines in the cut. I kept the failed Gemini lines in the log so the rejection is evidence, not a story.

The second hard stop was Cloudflare. Nine keyframes landed (about 185 seconds of latency, cost 0). Shot s10 timed out, and the retry was HTTP 429: the daily free allocation of 10,000 neurons was gone (F-003). The brief's estimate of 50–170 images did not match this account. I dropped s10 and let s09 carry the ending, rather than wait a day for one more frame (E-010). Caching meant the nine finished frames were not regenerated.

## A suggested practice that beat my instinct

My instinct was to trust the model the brief named, and to trust `status: ok`. The practice that beat that was logging every call and listening to the file before the next stage. The Kore take is in `runs.jsonl` as a success and in F-001 as a rejection. Without the log I would have "fixed" a language failure by regenerating blindly. With it, I could separate a 503 on the text model, a 429 on TTS, and a 200 that still spoke the wrong words.

The reference sheet did the same job for pictures. Four seeds, one kept (seed 201), and character shots were conditioned on that image. I would have written a new description of her face on every shot. The sheet made that unnecessary.

## A suggested practice that did not

The brief's moving-shot stage is Wan 2.2 image-to-video. I did not run it. There is no Wan line in `runs.jsonl`. After the neuron cap I did not want to spend the remaining day in a Kaggle queue, so `shots.py` moves each keyframe with FFmpeg `zoompan` (E-008, 24 seconds for nine clips). The storyboard still says `wan2.2` on four shots. The code ignores that field.

That fallback is allowed. It is also a practice I did not test. I cannot say Wan failed, or that Ken Burns looks better, because I never generated the clip. The honest result is narrower: a still that zooms does not drift into a different person, and it costs no GPU. A generated clip might have been more alive. I do not know. Writing `motion_engine` into the storyboard and then not reading it was the sloppy part, and it is recorded so the interview does not have to discover it.

## Beyond the floor

The extra work that changed a decision was the language, not a new feature. The brief says Gemini TTS covers a very long language list. On one Oromo sentence it did not. Addis did well enough to carry the film, and even Addis misread words until the voice and the padding changed (`Roobnis`, clipped edges). I stopped treating "the API supports your language" as a fact and started treating it as a hypothesis with a wav attached.

What I did not do, and will not claim: a second full cut in Amharic (the lines are in the storyboard, under `narration.am`, and they were never synthesized), a Wan-versus-open-model blind test, a LoRA, or a web app for relatives. One measured rejection was worth more than bolting those on after the quota was gone.

## What I would build next

A single narration stage that takes the voice name from the storyboard, synthesizes the same three hard lines on Gemini and on Addis, and writes a word-error count next to the log. Then one Wan clip, on a shot that is already a strong keyframe (s09), cached like the others, so the film can replace a zoom with a generated move without rerunning the eight that are fine.

The audience tests come before that. Three people, the radio cut, then the film, in their words.
