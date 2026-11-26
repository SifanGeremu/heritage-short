# Family film

A relative opens one page, answers three questions, and gets a short vertical film. The page does not read or write `storyboard.json`, and it does not write `outputs/film_9x16.mp4`. Each film goes to `outputs/family/<id>/`. Cost and latency for a real film are appended to `outputs/family/runs.jsonl`, not to `runs.jsonl`.

## Run

```bash
make family
```

Open http://127.0.0.1:8765

`FAMILY_DRY=1 make family` paints flat frames and a quiet tone, and calls no API. A real film needs `ADDIS-AI-API-KEY`, `CLOUDFLARE_ACCOUNT_ID`, and `CLOUDFLARE_API_TOKEN` in `.env`. One film is one portrait and three frames. Two films fill the free Cloudflare day. The voice is Addis `om-ayyaantuu`, a few birr. The person is painted. There is no photo upload. The film ends with "Made with AI".

```bash
.venv/bin/python family/board.py --self-check
.venv/bin/python family/render.py --self-check
```

## The sitting

Date:

Who:

Did she finish alone?

Where she stopped:

Did the film keep the name, the object, and the last line?

What it changed:
