VIRTUALENV_DIR := venv
REQUIREMENTS_FILE := requirements.txt

$(VIRTUALENV_DIR):
	virtualenv $(VIRTUALENV_DIR)
	$(VIRTUALENV_DIR)/bin/pip install -r $(REQUIREMENTS_FILE)

install: | $(VIRTUALENV_DIR)

.PHONY: _test
_test:
	python -m unittest discover -s tests

test: install _test

.PHONY: clean
clean:
	rm -rf $(VIRTUALENV_DIR) log