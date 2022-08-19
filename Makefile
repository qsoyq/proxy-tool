.PHONY: default format mypy build push


IMAGE_NAME := clpy9793/proxy-tool
PROJECT_NAME := proxy-tool

default: build push

format: refactor pre-commit

refactor:
	@yapf -r -i . 
	@isort . 
	@pycln -a .

pre-commit:
	@pre-commit run --all-file

mypy:
	@mypy .

build:
	docker build --platform linux/amd64 -t $(IMAGE_NAME) .

push:
	docker push $(IMAGE_NAME)
	if [ -n ${BARK_TOKEN} ]; then curl https://api.day.app/$(BARK_TOKEN)/$(PROJECT_NAME)%20push%20success; fi;
