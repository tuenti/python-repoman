all:: test

env_setup_for_development::
	@echo installing all requirements...
	@pip install -r requirements.txt
	@pip install -r requirements-dev.txt

	@echo setting up the development environment
	@python setup.py develop

env_setup_for_documentation::
	@echo installing all requirements...
	@pip install -r requirements-doc.txt

test::
	@echo launching tests...
	@py.test tests

coverage::
	@echo launching tests with coverage report...
	@py.test tests --cov repoman

publish::
	python setup.py sdist bdist_wheel upload


doc:: doc_from_code
	python setup.py build_sphinx
	@echo documentation available at $(shell pwd)/doc/build/html/index.html

doc_from_code::
	sphinx-apidoc repoman -o doc/source -f

clean::
	@echo removing PYC files...
	@find -name "*.pyc" -exec ${RM} "{}" \;

vclean:: clean
	@echo removing dist and build directories...
	@${RM} -r dist build
