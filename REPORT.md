# Report — Faaruun Hin Callisu

Assignment 1, AI-Content Generation. The repository is the pipeline. This note is what I set out to make, what the listeners changed, and what is still open.

## What I set out to make, and for whom

A film of about one minute for Oromo youth and the diaspora, and for families from Dambi Doolloo and Wallaga, watched first on a phone. The feeling at the end was fixed before any image call: grief turning into pride. A mother in a rain-lit room touches her son's guitar, and a generation that did not know him still sings.

The film is *Faaruun Hin Callisu*. Ten shots, Afaan Oromo narration, English subtitles, an instrumental score, both aspect ratios, and a card that says it was made with AI. Shot durations in `storyboard.json` sum to 79 seconds. The end card is 3 seconds. `outputs/radio_cut.mp4` is 82.000 seconds. `outputs/film_9x16.mp4` and `outputs/film_16x9.mp4` are 90.042 seconds, which is 90 seconds plus one frame at 24 fps. The picture is longer than the board because each line is slowed to 0.88× and the frame holds to the voice. `make film` is the command. The contract is `storyboard.json`.

## What I learned from listening

The first radio cut was not ready for anyone else. It is FAILURES F-002. About 45 words, a male voice (`om-bikila`) saying a woman's line, words cut off at the edges of the wav (`Roobnis` heard as `Romnis`), and a drone that made the silence feel like a horror sting. A listener who did not already know the story could not have said who the son was.

That listen changed the storyboard before the sittings below. The narration grew to the guitar, Qubee, the cassette, the notebook, the line he left her, and August 1996. The voice became Addis `om-ayyaantuu`. Each line is padded instead of trimmed. Shot s03's prompt is the mother with the neighborhood children and the chalk. F-009 is why those frames were not the ones that shipped.

On 26 November 2026 three people from the audience heard that cut with the screen face-down: Caaltuu (54), Boonaa (27), and Leensaa (21). Their words are in `DESIGN.md`. The story arrived. Caaltuu and Boonaa named Eebbisaa Addunyaa from Dambi Doolloo, the six strings, the hidden cassettes, Qubee, and *Haadha dhiiraa hin boo'in*, without the film saying his name. Leensaa needed the proverb and August 1996 in Finfinnee before she got there, and she said someone younger could hear a fictional singer.

What failed is the voice and the consonants. Caaltuu: "There's no age in her throat, no heaviness." Boonaa heard a synthetic narrator at the same temperature from the first line to the last, so he understood the pride more than he felt it. Leensaa heard *chukuliisaan* for *cuquliisaan* and said, "Okay, this is AI." *Q*, *c*, and *dh* collapsed. *Hin jiru* was clipped to "hin ju." *Weeddiste* was cut to "weeddi—". Boonaa thought the file had glitched. Leensaa waited for one plucked string and for singing in the rain, because the words promise both, and heard only rain.

The same day, Caaltuu, Boonaa, and Hannah (31, no Oromo) heard the English subtitle script from `outputs/assemble/subs_16x9.ass` read by a human, eyes closed. They did not watch the picture. Hannah thought the speaker was a widow until the proverb. She did not know who he is, because that text never said Eebbisaa, and she does not know what Qubee is or that Finfinnee is Addis Ababa. Boonaa, with a human voice this time, still heard "a narrator reciting a poem." The last card was the one-second line "word you wrote." Caaltuu thought the track had frozen. She had been told "Listen, my son," and "do not weep" was never answered. She waited again for a plucked string and heard none.

The same day, Girma, Geremew, and Amen watched a video. Geremew is the older viewer and speaks Oromo. Amen is the younger viewer and mostly read the English. Their words are in `DESIGN.md`, under the old-cut watch. That file was the 72.5-second picture from before storyboard v3, and the screen stayed black (F-010). Girma thought the video was not loading. Amen read the speaker as a wife or a girlfriend until "Mother of a hero" and "my son." Girma and Amen both said the "Made with AI" card broke the feeling. The card stayed, because assignment 2 grades it.

Chaltu (32), Beka (21), and Dawit (29) watched `outputs/film_9x16.mp4`. Chaltu already knew the history. Beka heard the calendar and the flat voice. Dawit needed the name spoken and the night the news arrived. Their words are the near-final sitting in `DESIGN.md`. The English says Eebbisaa at eight seconds and again at 1:07. s02's reason names the tea and the humming, the private memory in that shot. The voice stays `om-ayyaantuu`.

What the board holds, and who it answers, is the table in `DESIGN.md`. Caaltuu's "say his name" is the first word of s02 and the name again in s08. Hannah's missing gloss is s03, "our Oromo alphabet," and s05, "the capital." Caaltuu's unanswered proverb is s05, "do not cry," and s10, "Tonight, my son... I will not cry." Boonaa's "why tonight" is s07. The string Leensaa and Caaltuu waited for is s08's `music_cue`, `3.3s into` the shot, which is the gap after the words. s02's reason now says the tea and the humming, which is the private memory already in that shot's line. The voice is still `om-ayyaantuu`. `ETHICS.md` records that this is not his face and not his voice. s10 has no keyframe. `shots.py` copies the previous clip and logs a hold. That file is `outputs/shots/s10_886cac85.mp4`. `s10_hold9.mp4` is the earlier hand copy. There is still no chorus of children. *Gitaara*, *Qubee*, *cuquliisaan*, and *dhaloonni* are still this voice.

## The hardest problem

Gemini 3.8 Flash TTS is the model the brief points at, including for languages beyond English. It returned a valid wav for an Oromo greeting and the words were wrong (F-001, `runs.jsonl` status `ok`, latency 3.269 s, cost 0). I then hit HTTP 429 on the narration quota, fourteen times, and got no audio at all (F-005). A green log line was not a reading. A quota error was not a pronunciation problem. They felt the same from the outside: I still had no voice.

The fix was a provider that has Oromo voices, Addis, and a voice whose gender matches the speaker. `om-ayyaantuu` is the take in the film. The ten lines `outputs/narration/timing.json` points at are the 26 November retakes: all `ok`, 75.89 seconds of audio, 5.82 ETB of list price. The earlier nine-line figure, 4.59 ETB, is the cut the listeners heard. I kept the failed Gemini lines in the log so the rejection is evidence, not a story.

The second hard stop was Cloudflare. Nine keyframes landed (about 185 seconds of latency, cost 0). Shot s10 timed out, and the retry was HTTP 429: the daily free allocation of 10,000 neurons was gone (F-003). The brief's estimate of 50–170 images did not match this account. E-010 dropped s10 so the nine finished frames could ship. The listens put s10 back. The children-in-the-rain picture was never generated (F-009). Caching meant the nine finished frames were not regenerated. The missing picture is now a logged hold in `shots.py` (E-012), not a step that exists only in this paragraph.

## A suggested practice that beat my instinct

My instinct was to trust the model the brief named, and to trust `status: ok`. The practice that beat that was logging every call and listening to the file before the next stage. The Kore take is in `runs.jsonl` as a success and in F-001 as a rejection. Without the log I would have "fixed" a language failure by regenerating blindly. With it, I could separate a 503 on the text model, a 429 on TTS, and a 200 that still spoke the wrong words.

The reference sheet did the same job for pictures. Four seeds, one kept (seed 201), and character shots were conditioned on that image. I would have written a new description of her face on every shot. The sheet made that unnecessary.

## A suggested practice that did not

The practice was one contract. Every stage reads `storyboard.json`, and each shot's `duration_s` is part of that contract. My instinct after F-002 was that a clipped word is worse than a longer film, so the voice should set the length.

The radio cut still follows the board. The ten shot durations sum to 79 seconds, the end card adds 3, and `outputs/radio_cut.mp4` is 82.000 seconds. A line longer than its shot is sped to fit. s02, s04, s05, and s07 are still sped on that cut.

The picture export follows the wav. `picture_slots` in `pipeline/assemble.py` holds each frame for that line at 0.88× (`STORY_TEMPO`), plus the breath before the next line. `collect_inputs` copies `shot["duration_s"]` onto the shot and the timeline never reads it. Both exports are 90.042 seconds, which is 90 seconds plus one frame at 24 fps. The board says 79. The cut Chaltu, Beka, and Dawit watched is the voice's clock.

The contract still names the shots, the prompts, the seeds, and the line. On length, the instinct won. The film is one frame over the 60–90 second cap because the stage that exports it does not obey the durations in the file it claims as its contract.

## Beyond the floor

The extra work that changed a decision was the language, not a new feature. The brief says Gemini TTS covers a very long language list. On one Oromo greeting it did not (F-001). Addis did well enough to carry the film, and even Addis misread words until the voice and the padding changed (`Roobnis`, clipped edges). I stopped treating "the API supports your language" as a fact and started treating it as a hypothesis with a wav attached.

E-011 is that hypothesis on four slices of the current board, three Oromo and one Amharic. Gemini returned audio this time, cost 0, with no language code sent. Addis, with `om` or `am` sent, cost 1.2884 ETB. Addis Scribe counted 5 token edits on the Addis wavs and 13 on the Gemini wavs, out of 34 source tokens. `gitaarri` and `cuquliisni` survived Addis. Gemini wrote `gitaarrii` and `kalam`. On the teaching line Addis wrote `baleessuu` for `barreessuu` (F-011). In Amharic, Addis kept `ኤቢሳ` and Gemini wrote `ቢሳ`. The film stays on `om-ayyaantuu`. Scribe is an Addis model, not Caaltuu's ear, and there were not five blind listeners. Seventeen scribe lines in `runs.jsonl` have no timestamp and no latency. The logger omitted them. They were not backfilled. `log_scribe` now writes the latency. Those old rows do not have it.

The full Amharic board was priced and not rendered. `python pipeline/benchmark_lang.py --quote` uses the 75.89 seconds of Oromo in `timing.json` and the character counts of the Amharic lines already in `storyboard.json`, at 5 ETB per minute. The quote is 40.88 seconds and 3.4065 ETB. No provider was called. That is the decision: one counted comparison, plus a price for the cut I am not pretending to have made.

The family page is the other extra. A relative answers three things, a name, one object, and a last line, and `family/server.py` writes a three-shot vertical film to `outputs/family/<id>/` without reading or writing `storyboard.json`. `family/board.py --self-check` and `family/render.py --self-check` cover that path. The public page is a dry preview: flat frames, no Addis call, no Cloudflare call, so a stranger cannot spend the key. A real film is still `make family` on this machine. No relative has sat with it. The blank lines in `FAMILY.md` are that fact.

What I did not do, and will not claim: that second full cut, a Wan-versus-frontier blind test, or a LoRA.

## What I would build next

One Wan clip, on a shot that is already a strong keyframe (s09), cached like the others, so the film can replace a zoom with a generated move without rerunning the shots that are fine. Then the six frames F-009 could not get: the mother and the painted child, conditioned on `golden_480.jpg`, once the Cloudflare day resets. The four-line comparison is E-011. The open word inside it is `barreessuu`.

Caaltuu (54), Boonaa (27), and Leensaa (21) heard the Oromo radio cut. Caaltuu, Boonaa, and Hannah (31) heard the English lines with their eyes closed. Girma, Geremew, and Amen watched the 72.5-second picture, which was black and did not say his name. Chaltu (32), Beka (21), and Dawit (29) watched the 90.042-second film. The board says Eebbisaa. The voice is still too young, the child frames are still the earlier room, and the rain still has no one singing in it.
