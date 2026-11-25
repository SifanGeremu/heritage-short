.PHONY: validate narration radio pipeline keyframes shots music assemble film

PYTHON ?= .venv/bin/python

validate:
	$(PYTHON) pipeline/validate.py

narration:
	$(PYTHON) pipeline/stage_narration.py

radio:
	$(PYTHON) pipeline/stage_assemble.py

pipeline: narration radio

keyframes:
	$(PYTHON) pipeline/keyframes.py

shots:
	$(PYTHON) pipeline/shots.py

music:
	$(PYTHON) pipeline/music.py

assemble:
	$(PYTHON) pipeline/assemble.py

film: validate narration keyframes shots music assemble
