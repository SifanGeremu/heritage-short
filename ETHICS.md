# Ethics

## Consent

No living person's face or voice is in the film, and no consent form was collected because there is no likeness to authorize. The mother is a painted character. `character.is_real_person` is false. The narrator is Addis stock voice `om-ayyaantuu`, not a clone and not a family recording. Eebbisaa Addunyaa is named in the narration. He is a public historical figure. He is not pictured and he is not voiced. In the memory shots the child is a painted boy of about eight, and the other children are painted the same way. None of them is a portrait of him. The name was written into the storyboard because listeners could not tell who the son was without it. The story uses a real place (Dambi Doolloo), August 1996, and the guitar, the cassette, and Qubee. Those are the teller's material. They are not a likeness.

## Licences

| Piece | Terms used here |
| --- | --- |
| Addis AI Voices 2, `om-ayyaantuu` | Paid by audio length. The client prices it at 5 ETB per minute (`pipeline/providers/addis.py`). Output is generated speech for this film, not a sample of a private person. |
| Gemini API, including 3.8 Flash TTS | Used for smoke tests and rejected narration takes. Google's Gemini API terms cover the free tier. Those wavs are not in the finished film. Prompts sent there should be treated as eligible for Google's free-tier training use, so private family detail was kept out. |
| FLUX.2 klein 9B on Cloudflare Workers AI (`@cf/black-forest-labs/flux-2-klein-9b`) | This is the 9B checkpoint. The brief states that the 4B klein weights are Apache 2.0 and the 9B weights are non-commercial. The film was made on the free Workers AI allowance, for a coursework submission, not for sale. The 9B non-commercial term is the one that applies to these frames. |
| ACE-Step 1.5 | MIT licence. The project states that outputs may be used commercially. The score is instrumental, seeds 301–303, and seed 303 is the one in the film. |
| Wan 2.2 | Apache 2.0. Not used. No Wan clip is in `outputs/` or in `runs.jsonl`. |
| FFmpeg | Local tool for zoompan, the mix, subtitles, and both exports. The binary is not redistributed in this repo. |

## Labelling

The last three seconds of both exports are a card that reads "Made with AI". On 26 November 2026, Girma and Amen said that card, coming right after she will not cry, broke the feeling. It stays. The assignment grades that disclosure. The public post, when it goes up, uses the platform's AI-content disclosure. No metadata check was run, so none is claimed. Subtitles are burned in by FFmpeg and are not presented as something the image model wrote. No words were asked of the image model. The style block forbids readable text in the frame.

## Privacy

`.env` is gitignored. `runs.jsonl` stores prompts and seeds and does not store API keys. Provider errors are passed through `redact` before they are logged. The Oromo narration is the film's script, not a private letter. It was sent to Addis, and earlier drafts were sent to Gemini.
