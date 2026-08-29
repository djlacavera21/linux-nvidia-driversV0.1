.PHONY: install test check detect doctor plan clean

install:
	python3 -m pip install -e .

test:
	python3 -m unittest discover -s tests -v

check:
	python3 -m compileall -q src tests
	python3 -m unittest discover -s tests -v

detect:
	nvlx detect

doctor:
	nvlx doctor

plan:
	nvlx plan

clean:
	find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf build dist *.egg-info src/*.egg-info
