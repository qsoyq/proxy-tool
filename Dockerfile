FROM python:3.10

ENV TZ=Asia/Shanghai

WORKDIR /app/

ENV PYTHONPATH="/app:${PYTHONPATH}"

COPY pyproject.toml pyproject.toml

COPY poetry.lock poetry.lock

RUN pip install poetry -i https://mirrors.aliyun.com/pypi/simple

RUN poetry config virtualenvs.create false

RUN poetry install --no-dev

COPY src /app/

RUN mkdir -p /logs

EXPOSE 8000

CMD python main.py -p 8000
