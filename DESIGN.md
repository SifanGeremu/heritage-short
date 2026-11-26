# Design

## Audience

Oromo youth and the diaspora, families from Dambi Doolloo and Wallaga, and anyone who will watch a one-minute film on a phone in a family chat. The first frame is 9:16 for that chat. 16:9 exists for a laptop or a classroom screen.

## Intent

Written before the pictures. At the end they should feel grief turn into quiet pride: a singer can be silenced, and the song still gets sung by people who were not born when he was.

## Logline

An elderly mother in Dambi Doolloo plucks one string on her late son's dusty guitar and hears a new generation singing his melody back through the August rain.

Title: *Faaruun Hin Callisu* (The Song Will Not Fall Silent).

## Why each shot exists

| Shot | Seconds | Reason |
| --- | --- | --- |
| s01 | 8 | The room when he was small: the mother and the child together in the August rain. |
| s02 | 8 | Introduce the mother and establish the untouched guitar as the visual symbol of absence. |
| s03 | 7 | Show his cultural legacy beyond music: as a child he is with the neighborhood children, learning to write their names. |
| s04 | 8 | Show tangible devotion: preserving a silenced voice on an old cassette tape. |
| s05 | 8 | Connect his craft to language and ink—words that outlived the writer. |
| s06 | 8 | The emotional nadir: the heavy silence of August 1996 hanging over the house. |
| s07 | 8 | The active pivot: she breaks the silence herself instead of staying passive in grief. |
| s08 | 7 | Focus on the single physical gesture that reconnects past and present. |
| s09 | 8 | Land the core feeling: grief transforming into tear-bright maternal pride. |
| s10 | 9 | Close the proverb in Dambi Doolloo rain: the mother and the children are in the doorway, and she does not cry. |

Those sentences are the `reason` field on each shot in `storyboard.json`. The style block is fixed for every keyframe: painterly charcoal-and-oil, warm doorway against blue-gray rain, earth tones, grain, subject in the centre, no text inside the image. The mother is one description (late sixties, cream scarf, worn brown dress, silver hair) plus `outputs/reference/golden.jpg`, seed 201, scaled under 512 px as `golden_480.jpg` because klein refuses a larger reference.

## What changed after the first listen

Radio cut v1 was about 45 spoken words, a male Addis voice (`om-bikila`), clipped syllables, and a low drone on a black frame. Someone who does not already know Dembi Dollo could not tell who the son was. That listen is written up as FAILURES F-002. The storyboard changed before any more pictures were spent:

- Narration grew to a full telling: the guitar, the songs, Qubee, the cassette, the notebook, the line he left her, August 1996, and the voices beyond the door.
- The voice became a woman, Addis `om-ayyaantuu`. The line `Ani weellistuu miti` cannot be said by a male voice.
- Each wav is padded (250 ms in front, 350 ms after) and faded 15 ms, and it is not trimmed. v1 was cutting words in half.
- Shot s03's picture holds the guitar, the exercise book, and the chalk in one room, so the teaching is visible.
- The temp bed under the radio cut became soft rain instead of the drone.

Shot durations in storyboard v3 sum to 79 seconds. The 3-second end card brings the target to 82. The radio cut uses those shot lengths. A line longer than its shot is sped to fit, not given extra time.

## User test 1 (radio cut)

26 November 2026. Three listeners, screen face-down, so the picture could not help them. They heard the narration through to the end, and the rain bed fade out.

| Who | Age | Why they count |
| --- | --- | --- |
| Caaltuu | 54 | The mother's generation. She knows Dambi Doolloo, the cassettes, and the proverb without being told the plot. |
| Boonaa | 27 | An Oromo listener in the age of the diaspora audience. He hears both the history and the machine. |
| Leensaa | 21 | The phone audience. She did not arrive already knowing who the son was. |

### Who is speaking

All three found a mother in the words, and none of them found a mother in the voice.

Caaltuu: "In the story, it's a mother. A mother sitting alone in Dambi Doolloo while the August rain is falling, talking to her dead son. She says *ilma koo*, and 'I'm not a singer, just a mother who misses you.' If you ask my ears, she doesn't sound like a mother. She sounds like a young woman reading off a page, or a computer voice. There's no age in her throat, no heaviness."

Boonaa heard the same split: the text is the mother of a slain singer in an empty house, and the sound is "a radio narrator, almost synthetic, reading a mother's letter rather than the mother actually speaking it."

Leensaa, for the first ten seconds, thought the speaker was a lover or a sister. *Ilma koo* corrected her halfway through. *Haadha dhiiraa hin boo'in* settled it.

### Who he is, and what he did

Caaltuu and Boonaa named him before the film does. Caaltuu: "Eebbisaa Addunyaa. You don't even need the name. The second I heard Dambi Doolloo, the six-string guitar, and people hiding his cassettes to listen in secret, my heart knew. He sang for his people, fought for them with his music, and taught children Qubee Afaan Oromoo so they could write their own names."

Boonaa listed the same markers: Dambi Doolloo, the guitar, Qubee, lyrics in blue pen, the underground cassettes, and *Haadha dhiiraa hin boo'in* before he left for Finfinnee.

Leensaa needed longer. She had "an Oromo singer and teacher from Dambi Doolloo who fought through songs," and only the proverb plus August 1996 in Finfinnee produced "Ohhh, Eebbisaa." Her warning: the name is never spoken, so someone younger than her can hear a fictional singer.

### What happened to him

Caaltuu: "He left for Finfinnee, and in August of '96 a bullet silenced him there. *Isaan weellisaa ajjeesan malee, weedduu hin ajjeesne.* They killed the singer, not the song. After that day, her house stayed quiet for years."

Boonaa caught a calendar snag. *Bara 96* in Afaan Oromo sent him to the Ethiopian calendar for a moment. He had to convert it to see she meant Gregorian 1996, which is 1988 EC.

Leensaa heard a shooting in Finfinnee before he could come home. She noticed the film never says who fired. "A bullet" and "they" felt heavier to her, "like everybody already knows who they are."

### Where the listen broke

Boonaa left the story in three places. Around the guitar, the line stuttered into "gitaari rikkee… ribbii jaa kofaan," and he had to replay it to recover "with just six strings." After *Haadha dhiiraa hin boo'in*, the audio cut mid-word: "jattee naaf weeddi—" and then silence. He thought the file had glitched. Near the end, *dhaloonni haaraan* arrived as "aloonni haaraan," and only the next phrase, *kan gaafas hin dhalanne*, let him repair it.

Leensaa's breaks were sounds the words promised and the track did not play. She leaned in for one old string and heard nothing. At the end, "through the rain they're singing your voice back to you," she looked at the speaker. Screen off, there was rain and a voice, and no one singing.

Caaltuu lost the first sentence, clipped to "hin ju" instead of *hin jiru*, and almost lost *Qubee* because it was too soft. The pause after every sentence was the same length, "like a machine turning off and back on," and her attention left the room once or twice.

### Which words sounded wrong

Boonaa heard the ejectives and implosives flattened, an accent with no *q*, *c*, or *dh*:

- *Gitaarri kee* came out "gitaari rikkee."
- *Qubee* came out "ubee" or "kubee."
- *Qofa* and *qofaan* came out "kofa" and "kofaan," every time.
- *Qalama cuquliisaan* came out "kalama chukuliisaan."
- *Dhaloonni* lost *dh* and came out "aloonni."
- *Dhoksaatti*, *dhaggeeffatu*, *dhaabe*, and *dhaggeeffadhu* all lost *dh* and became a plain *d*.
- *Weeddiste* was cut to "weeddi—".

Caaltuu, on the first line: *roobni* sounded like "roomni," and *hin jiru* was swallowed. Near the end, *rooba keessaan* ("through the rain") came out short, like "your rain."

Leensaa's two that gave the method away: "gitaari rikkee" and "kalama chukuliisaan." "The second I heard *chukuliisaan*, I immediately thought, okay, this is AI."

### What they felt, and what they wanted said

The ending they described is the ending the film is for. Caaltuu: grief turning into strength, a tight chest in the empty house, then chills on "Tonight, my son, I will not cry," and pride that the voice did not die in Finfinnee. Leensaa called it heartbreak mixed with goosebumps, "a quiet defiance," and said the callback to *Haadha dhiiraa hin boo'in* almost did it. Boonaa: the script earns a bittersweet resolve, and right now "you understand what you're supposed to feel, more than you actually feel it," because the last line is delivered at the same flat temperature as the first.

What they asked her to add:

- Caaltuu: say his name once. "No mother sits in the dark talking to her dead son for a minute and a half without calling his name." One memory only a mother would have, not only the public history of Qubee and cassettes. And an *eebba*, a mother's blessing, at the end.
- Leensaa: two seconds of his melody, hummed, instead of announcing "I will try one note" and moving on. Or the night the news reached Dambi Doolloo.
- Boonaa: one honest line about the years between 1996 and tonight. She jumps from "this house stayed quiet" to "tonight I can't be quiet." Why tonight is the missing turn.

### What this test changes

The story is legible. The voice is not believable, and several Oromo consonants are still wrong. Those two findings stand even though v1 already fixed the male voice and the worst clipping.

The story is legible in Oromo to people who already know it. The voice is not believable, and several consonants are still wrong. The English listen the same day revises what the next cut should do. That combined list is at the end of User test 2.

## User test 2 (English lines, eyes closed)

26 November 2026. Same day, a second sitting. Caaltuu and Boonaa again, and Hannah in Leensaa's place. They did not watch the picture. The English lines in `outputs/assemble/subs_16x9.ass` were read aloud by a human voice, and they kept their eyes closed. The point was to hear the subtitle script with the Oromo pronunciation taken out of the way. Seven questions, in the order they were asked:

Hannah is not the core audience. She speaks English and has no Oromo background. She is the person the burned-in English is for. Caaltuu and Boonaa are the audience. Two of the three, plus one outsider.

| Who | Age | Why they were in the room |
| --- | --- | --- |
| Caaltuu | 54 | Bilingual Oromo mother. She heard the Oromo cut the same day. |
| Boonaa | 27 | Bilingual Oromo listener. He can hear when the English is translating a poem instead of a person. |
| Hannah | 31 | English only. She cannot use Dambi Doolloo, Qubee, or the proverb as a key. |

### 1. Who is speaking

Caaltuu again heard a grieving mother in the August rain at Dembi Dollo, talking to her dead son. The proverb does the work early. She does not say "my son" until nearly fifty seconds in. In the file that line is s07, about 0:50: "only a mother who misses you."

Hannah spent the first half-minute on a widow or a partner. "Your voice, the one that warmed this house, is gone." "Your guitar still rests where you left it." The proverb, and then "only a mother who misses you," is what turned the speaker into his mother.

Boonaa had the mother from the objects: guitar, old tape, notebook, empty house. The lines "Tonight, I refuse the silence" and "I pluck one worn string" made her "a narrator reciting a poem rather than a mother speaking quietly to herself." This was a human voice. The recital is in the writing.

### 2. Who he is

Caaltuu named Eebbisaa Addunyaa again, from Dembi Dollo, the six strings, Qubee, the secret cassettes, Finfinnee, and August 1996. "Anyone who knows our history recognizes him immediately even without his name."

Hannah did not. "I don't know who he is in real life because she never names him." From the words alone he is a protest singer and teacher from Dembi Dollo, fighting songs on six strings, children taught Qubee so they could write their names, cassettes heard in secret.

Boonaa split the room in one sentence. For Oromo listeners the proverb makes him unmistakably Eebbisaa Addunyaa. For anyone outside that history he is "an unnamed activist-poet rather than a specific real person."

### 3. What happened to him

Hannah had the plot: before Finfinnee he sang his mother the proverb, then "a bullet in Finfinnee silenced you." She noticed the film never says who held the gun, only a later "they": "They killed the singer—never the song."

Caaltuu: assassinated in Finfinnee in August 1996, and the house quiet since that night.

Boonaa heard a political killing without the name of the killer, because the secret cassettes come just before the bullet.

### 4. Where the listen broke

Hannah lost three things, all of them context the Oromo listeners did not need. *Qubee*: she did not know what it was, or why the children could not already write their names. *Dembi Dollo* and *Finfinnee*: without knowing Finfinnee is Addis Ababa, the trip has no geography and no danger. "You wrote these words in blue ink": which words? Eyes closed, she could not see a notebook.

Boonaa broke at the last line. She says "Listen, my son," and the track ends on "knows every word you wrote." "She told him to listen, and then it just ended. There was no sound, no singing, nothing to listen to." He also flagged the chopped tails. They are real cues in `subs_16x9.ass`, each about a second long, stranded on their own card: "house, is gone." "weep." "in silence." "one note."

Caaltuu thought the track had frozen on "knows every word you wrote." And again, on "I pluck one worn string," she waited for a guitar note. Nothing came, and she was out of the room.

### 5. Which words sounded wrong

This list is diction, not pronunciation. A person was reading.

Boonaa: "wrote" is the wrong verb for six strings, and it returns twice more ("wrote these words," "every word you wrote"). "Silenced," "silence," and "refuse the silence" land as three clunks. "Pluck" sounds like a stage direction. "August ninety-six" is casual beside "weep" and "doorway."

Caaltuu: "notebook of poems" is off, because what he wrote was lyrics. "I refuse the silence" sounds like a speech. On the page, anglicized "Dembi Dollo" next to Oromo "Finfinnee" does not match.

Hannah: "weep" is literary beside "hasn't" and "weren't." "Worn string" is the wrong adjective. A string is old, rusty, or frayed.

### 6. What they felt

Hannah got most of the way to grief turning into quiet pride, especially on "They killed the singer—never the song." Stopping on "knows every word you wrote" "left it feeling unfinished, like the final emotional beat was cut off."

Caaltuu was sharper. The film owes tears turning into strength. Instead "it leaves you suspended mid-breath." She set up "do not weep" in the middle and never came back to answer it. In this English text, she is right. s05 has the proverb. s09 does not answer it.

Boonaa: it earns a defiant release, builds on "Listen, my son," and stops short of the payoff.

### 7. What they wanted said

What they asked her to add:

- Caaltuu: finish. If she says "Listen," say what he should hear, voices in the rain singing his songs back, and close on "Tonight, my son, I will not weep." Say his name once: Eebbisaa.
- Hannah: two or three words for an outsider, "taught children Qubee, our alphabet." His name, so he is not anonymous. One memory only his mother would have.
- Boonaa: why tonight, after the years since 1996. And bring the Dembi Dollo rain back in the closing line, so the end touches the first sentence.

### What this test changed

Storyboard v3 is cut from these seven answers. The town spelling is `Dambi Doolloo` in the logline, the audience line, the shot reasons, and the narration, so it matches `Finfinnee`. `project.target_duration_s` is 82: 79 seconds across ten shots, plus the 3-second end card.

The lines that moved:

- His name is spoken. s02 opens on Eebbisaa. s08 says it again when she names the man they killed. The voice is still the stock mother, `om-ayyaantuu`. `ETHICS.md` records that this is not his face and not his voice.
- s01 is the rain on the roof when he was small, not "your voice is gone."
- s02 is the private memory: he hummed over his tea. The public history is no longer the only thing she says.
- s03 glosses Qubee in the sentence: "our Oromo alphabet."
- s04 says lyrics, not "notebook of poems."
- s05 calls Finfinnee the capital, and the proverb is "do not cry," not "do not weep."
- s06 says August 1996 and an empty quiet house. It no longer leans on the word "silence."
- s07 answers Boonaa's "why tonight": for years she could not touch the guitar, and tonight the quiet is too heavy.
- s08 no longer says she plucks. She says "Just one old string..." and the mix plays one. The line still says they killed the singer, not the song.
- s09 is "Listen, my son" and the children who were not born then. s10 is the sound she told him to listen for: the Dambi Doolloo rain, his songs coming back, and "Tonight, my son... I will not cry."

The pipeline changes from the same sitting:

- `subs_16x9.ass` and `subs_9x16.ass` had stopped on s09 because the board no longer contained s10. The writer now stamps each cue with its shot id and refuses to finish if the subtitle blocks are not s01–s10, or if s10 runs into the end card. F-007.
- Captions break on clause marks instead of a character window, so a card is not "weep." or "one note." on its own. F-008.
- At 1.5 seconds into s08 the radio cut mixes a synthesized A3 pluck (220 Hz) that rings about 2.5 seconds. From s09 the bed adds a warm A-minor hum, `cue_part2_hope`, ducked under the voice and louder in the pauses and after the last line.

## User test 3 (the video)

26 November 2026. Three people watched a video and answered the same seven questions. Girma. An older viewer who speaks Oromo. A younger viewer who mostly read the English words at the bottom. The notes do not give the second and third names.

### 1. Who is speaking

Girma: a mother sitting alone in Dembi Dollo in the rain, talking to her son who died. "Her voice sounded a bit too young and flat for a mother, though."

The older viewer heard the same person, a mother sitting alone in Dembi Dollo talking to her dead son. "She didn't sound like a mother to me, though—more like a phone voice reading a message."

The younger viewer, reading the English, thought at first it was a wife or a girlfriend missing someone, until the line "Mother of a hero" and the words "my son."

### 2. Who he is, and what he did

Girma named Eebbisaa Addunyaa. He played guitar, sang for his people, and taught kids Qubee so they could write their own names.

The older viewer named him too. Eebbisaa Addunyaa played guitar, sang for his people, and taught children how to read and write Afaan Oromoo.

The younger viewer had a singer and teacher from Dembi Dollo who used his guitar to fight for his people and taught kids how to write their names. "I didn't know who he was in real life."

### 3. What happened to him

Girma and the older viewer: he went to Finfinnee and was shot there in August 1996.

The younger viewer: he was shot in Finfinnee in August '96, and her house stayed quiet after that.

### 4. Where they stopped understanding

Girma followed the story on the English words at the bottom. The break was the picture. "I just got confused why the screen stayed completely black—I thought the video wasn't loading—and when she said 'Look' and 'Listen,' there wasn't anything to see or hear."

The older viewer kept waiting for a picture and wondered if the phone was stuck. Halfway through, she stopped in the middle of a word and did not finish it.

The younger viewer did not know what *Qubee* meant, or where *Finfinnee* is. When she said she plucked a string and told him to listen, "I only heard rain—no guitar and no people singing."

### 5. Which words sounded wrong

Girma heard *gitaara*, *Qubee*, *qalama cuquliisaan*, and *dhaloonni* come out weird, and one word in the middle cut off before she finished it.

The older viewer: *Gitaarri kee* and *qalama cuquliisaan* sounded twisted, *hin jiru* right at the start was swallowed, and *dhaloonni* near the end was off.

The younger viewer does not speak Oromo well, and noticed the one cut-off in the middle. In the English words, "weep" felt stiff beside the rest of the line.

### 6. What they felt

The ending they described is the ending the film is for, and then the card took two of them out of it.

Girma: sad at first, then proud and strong when she says she will not cry tonight. "Seeing 'Made with AI' pop up right after kind of broke the feeling, though."

The older viewer: deep sadness first, then pride that the young ones still carry his songs.

The younger viewer: sad, then hopeful and strong. "'Made with AI' showing up right at the end took me out of the mood."

### 7. What they wanted said

Girma: say his name at least once, Eebbisaa, and share one small everyday memory of him at home, not only his music.

The older viewer: call him by his name, Eebbisaa, and say one mother's blessing for him before the end.

The younger viewer: tell us his name, and give a small hint of what Qubee is, so someone who did not grow up with it still gets it.

### What this test changed

The notes land on two files that were both on disk.

`outputs/radio_cut.mp4` is a black frame with the v3 English burned in, including "Eebbisaa" and "Qubee—our Oromo alphabet" and "do not cry." The guitar note in that mix started 1.5 seconds into s08, under the words "Just one old string...", so a phone speaker heard rain.

`outputs/film_9x16.mp4` was still the 72-second picture export from before storyboard v3. At four seconds she is on the stool and the burned line is "your voice, the one that warmed this." That export says "weep," opens on *hin jiru*, and never says his name. "Look," "pluck," and the swallowed *hin jiru* belong to that cut.

From this sitting:

- The picture films are rebuilt on the v3 lines and the frames already on disk. The captions say his name, the tea, Qubee as our Oromo alphabet, Finfinnee the capital, and "do not cry." s01 still says "my son" in the first line, which is the answer to the wife-or-girlfriend misread.
- s10 holds the s09 doorway frame. The children-in-the-rain picture was not generated. F-009.
- The A3 pluck moves to 3.3 seconds into s08, the quiet after "Just one old string...", and it is louder. It is in the radio cut and in the picture mix. It is one note, not children singing. The score is still the bed under "Listen."
- The voice stays Addis `om-ayyaantuu`. Three sittings have called her young and flat. This key has no older voice that has been heard and kept.
- "Made with AI" stays on the last three seconds. Assignment 2 grades that card.
- A mother's blessing was asked again. s10 is already 8.4 seconds of speech inside a 9-second shot. Another clause would speed the last line, which is the cut-off they heard on the long lines (s02, s04, s05, s07 are still sped on the radio cut).
- *gitaara*, *Qubee*, *cuquliisaan*, and *dhaloonni* are still this voice. That is the open problem in F-001.

## User test 4 (the 90-second film)

26 November 2026. Chaltu, Beka, and Dawit watched `outputs/film_9x16.mp4`. No ages were given. The English on that file says Eebbisaa at eight seconds and again at 1:07. They still said the voice never landed his name. The words below are theirs.

### 1. Who is speaking

Chaltu: It's a mother, an older mother sitting alone in her house in Dembi Dollo while it's raining, talking to her son who passed away. Though honestly, if you only go by the sound of the voice, she sounds too young and too smooth, like a radio announcer or a computer voice reading a script rather than a real mother who has carried grief for decades.

Beka: At the very beginning, "Ammas hagayya, roobni Dambii Doolloo...", he thought it was just a narrator setting a scene. He didn't realize it was the mother herself until she said "Haadha dhiiraa hin boo'in" and called him "ilma koo."

Dawit: For the first thirty seconds he wasn't sure if it was a wife, a sister, or a narrator. Once she said "ani weellistuu miti, ilma koo, haadha si yaaddu qofa," it clicked completely.

### 2. Who is she talking about, and what did he do

Chaltu: Even though she never says his name, any Oromo person knows right away she's talking about Eebbisaa Addunyaa. Dembi Dollo, the six-string guitar, teaching Qubee, Haadha dhiiraa, August '96. She says he wasn't just a singer; he used his guitar to make songs that stood up for his people, he taught children Qubee Afaan Oromoo so they could write their own names, he wrote lyrics in a notebook with a blue pen, and people used to listen to his cassettes in secret.

Beka liked the detail about the blue ink and the secret cassettes. Right before he left for Finfinnee, he sang "Haadha dhiiraa hin boo'in" for her. That felt very real.

Dawit noticed she never actually said his name. He caught that it was her son, a protest singer and Qubee teacher from Dembi Dollo whose songs people hid to listen to. When she said August '96 in Finfinnee he put it together, but if someone listening didn't already know the history, they'd only know he was a beloved Oromo singer who taught kids to read and write.

### 3. What happened to him

Dawit: He went to Finfinnee, and in August 1996 a bullet stopped his voice. They killed him there. After that day, his guitar just stayed where he left it, and the house went silent for years.

Chaltu: She puts it very gently at first, "rasaasni Finfinneetti sagalee kee dhaabe," and then later she says it straight: "isaan weellisaa ajjeesan malee weedduu hin ajjeesne." She doesn't say who pulled the trigger or how it happened, just "a bullet" and "they."

Beka: When she said "bara sagaltamii ja'a," his brain hesitated, switching between the Ethiopian calendar and the Gregorian calendar, because August 1996 is '88 in our calendar, so he had to double-check.

### 4. Where they stopped understanding

Beka: Right near the start, around the guitar line. When she said "ribbii ja'a qofaan," it came out mashed together like "ribbii jaakofaan." He paused and thought, "Wait, who is Jaakofaan?" before realizing she meant six strings only.

Dawit: Twice. First, right after "Haadha dhiiraa hin boo'in jettee naaf...", the word cut off mid-air. His brain stalled waiting for the rest of the sentence. Near the end, when she said "balbala koo duubaan...", he heard "aloonni haaraan." He had no idea what aloonni was until she said "kan gaafas hin dhalanne," and then he went, "Oh, dhaloonni, a new generation."

Chaltu: That "aloonni" part tripped her up too. Earlier, when she said "Qubee Afaan Oromoo," it came out so soft without the Q that she had to catch it from context. And "rooba keessaan" at the end sounded a bit like "rooba keessan" ("your rain") instead of "through the rain."

### 5. Which words sounded wrong

Chaltu: Almost every word with Oromo dh or q sounded foreign or flat. That is what makes it sound like a machine voice.

- Haadha dhiiraa came out like "haada diiraa."
- Dhaabe ("stopped") sounded like "daabe."
- Dhoksaatti and dhaggeeffadhu lost the dh completely ("doksaatti," "daggeeffadu").
- Dhaloonni lost the whole start of the word and became "aloonni."
- Qubee sounded like "ubee," and qalama cuquliisaan sounded like "kalama cukuliisaan."

Beka: On top of the pronunciation, two words are physically clipped at the edits. Weeddiste cuts off sharply at "naaf wedd—" around the middle. Ol kaa'eera gets trimmed at the end so it sounds like "ol kaayer." And gitaarri kee has a weird extra d sound in it, almost like "gitaardikee."

Dawit: "gitaardikee" and "jaakofaan" stood out right away, and even the very first "roobni" sounded a little like "roomni." And "hin jiru" at the end of the first sentence clipped tight like "hinju."

### 6. What a person should feel at the end

Chaltu: A heavy chest turning into pride. Quiet goosebumps, tears, because the mother says, "Tonight, my son, I will not cry." Grief that didn't break her, because his voice survived him.

Beka: The words aim right for that, especially "they killed the singer, not the song" and "tonight I won't cry." Listening with his eyes closed, he only felt it in his head, not in his stomach. The voice stays the same flat speed from start to finish, and when she says "listen, my son, I'll try one worn-out string" and "through the rain they are singing your voice back to you," he strained his ears expecting a real guitar string or faint voices singing outside in the rain. Without that, the ending feels a little empty.

Dawit: He knew what he was supposed to feel, bittersweet, hopeful, proud, and the script is strong enough to almost get him there. If a real human mother's voice cracked slightly before steadying on "ani hin boo'u," it would wreck him in a good way.

### 7. What they would tell her to say

Chaltu: Say his name, "Eebbisaa koo." A mother talking to her dead son in the rain wouldn't only call him ilma koo like a poem; she would whisper his name at least once. Add one small, ordinary memory that only a mother holds, like how he looked eating at the table, or tuning that guitar late at night, and end with a real mother's blessing, "nagaan boqodhu." Right now she remembers him mostly as a hero. A mother remembers her boy too.

Dawit: Say his name early on, or at least once, so people listening without a screen aren't piecing together a riddle. There's a big jump from him singing "Haadha dhiiraa" to suddenly being dead in Finfinnee. Even one short line about the night she heard the news, or how the house fell quiet that morning, would make the pain land much harder.

Beka: One line about passing the notebook on. She kept his cassettes and lyric book hidden all these years, so who is she opening them for tonight? Even just saying "I'm opening the door now" before "tonight I won't cry" would tie the silent house to the new generation outside.

### What this sitting changed

They watched the current film, and the voice still hid the name the picture already prints. s02 and s08 were left as they are. Nothing in the pipeline was edited from these three. Still open, in their words: the voice is too young and too even, *dh* and *q* are still flat, they wanted a real string and voices in the rain, a mother's blessing (*nagaan boqodhu*), the night the news reached the house, and one line about who the notebook is being opened for.
