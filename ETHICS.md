# Ethics

## Consent

The film is a fictional tribute. The person on screen is a stylized, painterly Oromo mother in Dembi Dollo. She is not a portrait of a living or a dead person, and the storyboard marks her `is_real_person: false`. No real face, name, or voice is reproduced. The narration is Addis AI voice `om-ayyaantuu`, a stock voice, not a clone of anyone in the family. No home recording was uploaded to a provider.

The story uses a real place (Dembi Dollo), a real month in the memory it is drawn from (August 1996), and a real craft (Qubee, the guitar, the cassette). Those are the teller's material. They are not a likeness.

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

The last three seconds of both exports are a card that reads "Made with AI". The public post, when it goes up, uses the platform's AI-content disclosure. SynthID or C2PA metadata that a provider embedded is left in the file. Subtitles are burned in by FFmpeg and are not presented as something the image model wrote. No words were asked of the image model. The style block forbids readable text in the frame.

## Privacy

`.env` is gitignored. `runs.jsonl` stores prompts and seeds and does not store API keys. Provider errors are passed through `redact` before they are logged. The Oromo narration is the film's script, not a private letter. It was sent to Addis, and earlier drafts were sent to Gemini.
