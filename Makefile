.PHONY: validate narration radio pipeline reference keyframes shots music assemble film family

PYTHON ?= .venv/bin/python

validate:
	$(PYTHON) pipeline/validate.py

narration:
	$(PYTHON) pipeline/stage_narration.py

radio:
	$(PYTHON) pipeline/stage_assemble.py

pipeline: narration radio

reference:
	$(PYTHON) pipeline/reference_sheet.py

keyframes:
	$(PYTHON) pipeline/keyframes.py

shots:
	$(PYTHON) pipeline/shots.py

music:
	$(PYTHON) pipeline/music.py

assemble:
	$(PYTHON) pipeline/assemble.py

film: validate narration reference keyframes shots music assemble

family:
	$(PYTHON) family/server.py
