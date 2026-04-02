FROM python:3.11.11
# TODO: upgrade base image

ENV TZ=Asia/Shanghai

WORKDIR /app/

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml pyproject.toml

RUN pip install uv

RUN uv sync

COPY src /app/

RUN mkdir -p /logs

EXPOSE 8000

CMD ["uv", "run", "python", "main.py", "-p", "8000"]
