init:
	pip install pipenv
	pipenv install --dev

test:
	pipenv run py.test --cov-config .coveragerc --cov=s3tree
