init:
	pip install tox

test:
	tox

test36:
	tox -e py36
