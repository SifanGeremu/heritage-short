# Report — Faaruun Hin Callisu

Assignment 1, AI-Content Generation. The repository is the pipeline. This note is what I set out to make, what the listeners changed, and what is still open.

## What I set out to make, and for whom

A film of about one minute for Oromo youth and the diaspora, and for families from Dembi Dollo and Wallaga, watched first on a phone. The feeling at the end was fixed before any image call: grief turning into pride. A mother in a rain-lit room touches her son's guitar, and a generation that did not know him still sings.

The film is *Faaruun Hin Callisu*. Ten shots, Afaan Oromo narration, English subtitles, an instrumental score, both aspect ratios, and a card that says it was made with AI. Shot durations in `storyboard.json` sum to 79 seconds. The end card is 3 seconds. `outputs/radio_cut.mp4` is 82.000 seconds. `outputs/film_9x16.mp4` and `outputs/film_16x9.mp4` are 90.042 seconds, which is 90 seconds plus one frame at 24 fps. The picture is longer than the board because each line is slowed to 0.88× and the frame holds to the voice. `make film` is the command. The contract is `storyboard.json`.

## What I learned from listening

The first radio cut was not ready for anyone else. It is FAILURES F-002. About 45 words, a male voice (`om-bikila`) saying a woman's line, words cut off at the edges of the wav (`Roobnis` heard as `Romnis`), and a drone that made the silence feel like a horror sting. A listener who did not already know the story could not have said who the son was.

That listen changed the storyboard before the three sittings below. The narration grew to the guitar, Qubee, the cassette, the notebook, the line he left her, and August 1996. The voice became Addis `om-ayyaantuu`. Each line is padded instead of trimmed. Shot s03 was meant to show the book and the chalk, not only the guitar.

On 26 November 2026 three people from the audience heard that cut with the screen face-down: Caaltuu (54), Boonaa (27), and Leensaa (21). Their words are in `DESIGN.md`. The story arrived. Caaltuu and Boonaa named Eebbisaa Addunyaa from Dambi Doolloo, the six strings, the hidden cassettes, Qubee, and *Haadha dhiiraa hin boo'in*, without the film saying his name. Leensaa needed the proverb and August 1996 in Finfinnee before she got there, and she said someone younger could hear a fictional singer.

What failed is the voice and the consonants. Caaltuu: "There's no age in her throat, no heaviness." Boonaa heard a synthetic narrator at the same temperature from the first line to the last, so he understood the pride more than he felt it. Leensaa heard *chukuliisaan* for *cuquliisaan* and said, "Okay, this is AI." *Q*, *c*, and *dh* collapsed. *Hin jiru* was clipped to "hin ju." *Weeddiste* was cut to "weeddi—". Boonaa thought the file had glitched. Leensaa waited for one plucked string and for singing in the rain, because the words promise both, and heard only rain.

The same day, Caaltuu, Boonaa, and Hannah (31, no Oromo) heard the English subtitle script from `outputs/assemble/subs_16x9.ass` read by a human, eyes closed. They did not watch the picture. Hannah thought the speaker was a widow until the proverb. She did not know who he is, because that text never said Eebbisaa, and she does not know what Qubee is or that Finfinnee is Addis Ababa. Boonaa, with a human voice this time, still heard "a narrator reciting a poem." The last card was the one-second line "word you wrote." Caaltuu thought the track had frozen. She had been told "Listen, my son," and "do not weep" was never answered. She waited again for a plucked string and heard none.

The same day, three people watched a video. Girma, an older viewer who speaks Oromo, and a younger viewer who mostly read the English. Their words are in `DESIGN.md`, User test 3. Girma and the older viewer named Eebbisaa Addunyaa, the guitar, and the shooting in Finfinnee in August 1996. The younger viewer did not know who he was in real life, and read the speaker as a wife or a girlfriend until "Mother of a hero" and "my son." The screen stayed black. Girma thought the video was not loading. When she said "Look" and "Listen," and when she said she plucked a string, there was nothing to see and only rain to hear. The voice was still too young and flat: the older viewer called it a phone voice reading a message. *Gitaara*, *Qubee*, *qalama cuquliisaan*, *dhaloonni*, and a swallowed *hin jiru* were still wrong, and one word was cut off in the middle. "Weep" felt stiff. Sad, then proud, is what they felt, and Girma and the younger viewer both said the "Made with AI" card, right after that, broke it. They still asked her to say Eebbisaa, to give one memory of him at home, a mother's blessing, and a hint of what Qubee is. That file was the 72.5-second picture export from before storyboard v3. F-010.

Chaltu, Beka, and Dawit heard that same earlier cut, the one that never says his name. Their words are User test 4 in `DESIGN.md`. Beka had his eyes closed. They asked for "Eebbisaa koo," a mother's blessing (*nagaan boqodhu*), the night the news arrived, and one line about who the notebook is opened for. The board was not edited again from that sitting.

The first three sittings are what the board on disk answers. The name is spoken: s02 opens on Eebbisaa, and s08 says it again. The voice is still the stock mother, `om-ayyaantuu`. `ETHICS.md` records that this is not his face and not his voice. s10 closes the proverb on "Tonight, my son... I will not cry," with the Dambi Doolloo rain in the line. s03 glosses Qubee as our Oromo alphabet. s05 calls Finfinnee the capital, and "weep" is "do not cry." s02 is the private memory, tea and humming. The picture films were cut again on those lines. s10 has no keyframe of its own, so it holds the s09 doorway frame. The guitar note is one synthesized pluck in the quiet after "Just one old string...". There is still no chorus of children. The voice is still young, and *gitaara*, *Qubee*, *cuquliisaan*, and *dhaloonni* are still this voice. "Made with AI" stays on the last three seconds, because assignment 2 grades that card.

## The hardest problem

Gemini 3.8 Flash TTS is the model the brief points at, including for languages beyond English. It returned a valid wav for an Oromo greeting and the words were wrong (F-001, `runs.jsonl` status `ok`, latency 3.269 s, cost 0). I then hit HTTP 429 on the narration quota, fourteen times, and got no audio at all (F-005). A green log line was not a reading. A quota error was not a pronunciation problem. They felt the same from the outside: I still had no voice.

The fix was a provider that has Oromo voices, Addis, and a voice whose gender matches the speaker. `om-ayyaantuu` is the take in the film. The ten lines `outputs/narration/timing.json` points at are the 26 November retakes: all `ok`, 75.89 seconds of audio, 5.82 ETB of list price. The earlier nine-line figure, 4.59 ETB, is the cut the listeners heard. I kept the failed Gemini lines in the log so the rejection is evidence, not a story.

The second hard stop was Cloudflare. Nine keyframes landed (about 185 seconds of latency, cost 0). Shot s10 timed out, and the retry was HTTP 429: the daily free allocation of 10,000 neurons was gone (F-003). The brief's estimate of 50–170 images did not match this account. E-010 dropped s10 so the nine finished frames could ship. The listens put s10 back as narration and as a hold on the s09 frame. The children-in-the-rain picture was never generated (F-009). Caching meant the nine finished frames were not regenerated.

## A suggested practice that beat my instinct

My instinct was to trust the model the brief named, and to trust `status: ok`. The practice that beat that was logging every call and listening to the file before the next stage. The Kore take is in `runs.jsonl` as a success and in F-001 as a rejection. Without the log I would have "fixed" a language failure by regenerating blindly. With it, I could separate a 503 on the text model, a 429 on TTS, and a 200 that still spoke the wrong words.

The reference sheet did the same job for pictures. Four seeds, one kept (seed 201), and character shots were conditioned on that image. I would have written a new description of her face on every shot. The sheet made that unnecessary.

## A suggested practice that did not

The brief's moving-shot stage is Wan 2.2 image-to-video. I did not run it. There is no Wan line in `runs.jsonl`. After the neuron cap I did not want to spend the remaining day in a Kaggle queue, so `shots.py` moves each keyframe with FFmpeg `zoompan` (E-008, 24 seconds for nine clips). The storyboard still says `wan2.2` on four shots. The code ignores that field.

That fallback is allowed. It is also a practice I did not test. I cannot say Wan failed, or that Ken Burns looks better, because I never generated the clip. The honest result is narrower: a still that zooms does not drift into a different person, and it costs no GPU. A generated clip might have been more alive. I do not know. Writing `motion_engine` into the storyboard and then not reading it was the sloppy part. `shots.py` now reads the field and prints the fallback. s01, s02, s06, and s07 still say `wan2.2`. The clips on disk are still the zoom.

## Beyond the floor

The extra work that changed a decision was the language, not a new feature. The brief says Gemini TTS covers a very long language list. On one Oromo greeting it did not (F-001). Addis did well enough to carry the film, and even Addis misread words until the voice and the padding changed (`Roobnis`, clipped edges). I stopped treating "the API supports your language" as a fact and started treating it as a hypothesis with a wav attached.

E-011 is that hypothesis on four slices of the current board, three Oromo and one Amharic. Gemini returned audio this time, cost 0, with no language code sent. Addis, with `om` or `am` sent, cost 1.2884 ETB. Addis Scribe counted 5 token edits on the Addis wavs and 13 on the Gemini wavs, out of 34 source tokens. `gitaarri` and `cuquliisni` survived Addis. Gemini wrote `gitaarrii` and `kalam`. On the teaching line Addis wrote `baleessuu` for `barreessuu` (F-011). In Amharic, Addis kept `ኤቢሳ` and Gemini wrote `ቢሳ`. The film stays on `om-ayyaantuu`. Scribe is an Addis model, not Caaltuu's ear, and there were not five blind listeners.

What I did not do, and will not claim: a second full cut in Amharic, a Wan-versus-frontier blind test, a LoRA, or a web app for relatives. One counted comparison was worth more than bolting those on.

## What I would build next

One Wan clip, on a shot that is already a strong keyframe (s09), cached like the others, so the film can replace a zoom with a generated move without rerunning the shots that are fine. Then the six frames F-009 could not get: the mother and the painted child, conditioned on `golden_480.jpg`, once the Cloudflare day resets. The four-line comparison is E-011. The open word inside it is `barreessuu`.

Caaltuu, Boonaa, and Leensaa heard the Oromo radio cut. Caaltuu, Boonaa, and Hannah heard the English lines with their eyes closed. Girma, an older Oromo viewer, and a younger viewer who read the English watched the 72.5-second picture, which was black and did not say his name. The board and the 90-second exports now say Eebbisaa. The voice is still too young, the child frames are still the earlier room, and the rain still has no one singing in it.
