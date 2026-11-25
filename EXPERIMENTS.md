# Experiments

## E-001. Validation stops when a shot has no reason

Hypothesis: `make validate` accepts the current storyboard, and deleting one shot `reason` makes it fail with that field's path.

Change: Ran `make validate` on `schema/storyboard.json`. Removed `shots[0].reason` from shot `s01` and ran `make validate` again. Restored the original file bytes afterward.

Result: The intact board printed `ok` and exited 0. Shot `duration_s` values sum to 75, inside 60–90, and ids `s01`–`s10` are unique. With `reason` removed, the validator printed `$.shots[0].reason: 'reason' is a required property` and exited 1 (`make` reported `Error 1`). After the field was restored, `make validate` passed again.

Golden reference: seed 201. Reason: She looks straight at us, calm and still, so the face is easy to recognise in later shots. The cream scarf, the worn brown dress, and her hands are all in the frame. That is a person the other shots can follow, not a guess.

ACE-Step 1.5 on Kaggle, three instrumental candidates. GPU minutes: 1.701.

- seed 301, `music_301.wav`: latency 18.373s
- seed 302, `music_302.wav`: latency 13.288s
- seed 303, `music_303.wav`: latency 13.302s
