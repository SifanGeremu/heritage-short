# Design

## Audience

Oromo youth and the diaspora, families from Dembi Dollo and Wallaga, and anyone who will watch a one-minute film on a phone in a family chat. The first frame is 9:16 for that chat. 16:9 exists for a laptop or a classroom screen.

## Intent

Written before the pictures. At the end they should feel grief turn into quiet pride: a singer can be silenced, and the song still gets sung by people who were not born when he was.

## Logline

An elderly mother in Dembi Dollo, alone with her son's guitar, plays one note and hears young voices carrying his melody back through the August rain.

Title: *Faaruun Hin Callisu* (The Song Will Not Fall Silent).

## Why each shot exists

| Shot | Seconds | Reason |
| --- | --- | --- |
| s01 | 8 | Anchor place and season: August rain in a Dembi Dollo room, before we see her. |
| s02 | 8 | Introduce the mother and the untouched guitar, the object that stands in for her son. |
| s03 | 7 | His work was not only songs. He taught children Qubee so they could write their names. |
| s04 | 8 | Devotion you can hold: she kept his voice on a cassette. |
| s05 | 8 | The poem notebook. The words outlived the writer. |
| s06 | 9 | The low point. August 1996, and the house goes quiet. |
| s07 | 8 | She is the one who breaks the silence. Grief stops being passive. |
| s08 | 6 | One gesture: her hand on one string. Past and present meet there. |
| s09 | 8 | The feeling the film is for. A close-up, tear-bright, proud, turned toward the door. |

The same sentences are the `reason` field on each shot in `schema/storyboard.json`. The style block is fixed for every keyframe: painterly charcoal-and-oil, warm doorway against blue-gray rain, earth tones, grain, subject in the centre, no text inside the image. The mother is one description (late sixties, cream scarf, worn brown dress, silver hair) plus `outputs/reference/golden.jpg`, seed 201, scaled under 512 px as `golden_480.jpg` because klein refuses a larger reference.

## What changed after the first listen

Radio cut v1 was about 45 spoken words, a male Addis voice (`om-bikila`), clipped syllables, and a low drone on a black frame. Someone who does not already know Dembi Dollo could not tell who the son was. That listen is written up as FAILURES F-002. The storyboard changed before any more pictures were spent:

- Narration grew to a full telling: the guitar, the songs, Qubee, the cassette, the notebook, the line he left her, August 1996, and the voices beyond the door.
- The voice became a woman, Addis `om-ayyaantuu`. The line `Ani weellistuu miti` cannot be said by a male voice.
- Each wav is padded (250 ms in front, 350 ms after) and faded 15 ms, and it is not trimmed. v1 was cutting words in half.
- Shot s03's picture holds the guitar, the exercise book, and the chalk in one room, so the teaching is visible.
- The temp bed under the radio cut became soft rain instead of the drone.

Shot durations in the board sum to 70 seconds. The spoken lines run about 60 seconds before the 0.88× slowdown. The export, with fades and the end card, is 72.5 seconds.

## User test 1 (radio cut)

The assignment asks for three people from this audience, their words, and a storyboard change made because of them. This repository has the maker's listening pass above. It does not yet have three named listeners.

Play `outputs/radio_cut.mp4` to three people who match the audience. Write their names, the date, and what they actually said. Then change one thing in `schema/storyboard.json` and name that change here. Do not invent the quotes. The interview asks for this out loud.

## User test 2 (near-final cut)

Same rule, with `outputs/film_9x16.mp4`. Three people, what they said, what you changed after. The 16:9 file is the same cut with the portrait frame centred and the sides blurred.

## What I will not pretend

No audience quotes are filled in above, because none were recorded in the project. A grader who asks "what did they say?" has to hear it from you.
