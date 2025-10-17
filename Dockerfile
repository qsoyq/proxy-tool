FROM python:3.10.17
# TODO: upgrade base image

ENV TZ=Asia/Shanghai

WORKDIR /app/

COPY pyproject.toml pyproject.toml

RUN pip install uv

RUN uv sync

COPY src /app/

RUN mkdir -p /logs

EXPOSE 8000

CMD ["uv", "run", "python", "main.py", "-p", "8000"]
