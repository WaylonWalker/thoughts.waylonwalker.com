FROM python:3.11-slim
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app
COPY pyproject.toml /app
COPY thoughts/__about__.py /app/thoughts/__about__.py
COPY README.md /app
RUN pip3 install --no-cache-dir --root-user-action=ignore --upgrade pip
RUN pip3 install --no-cache-dir --root-user-action=ignore '.[all]'
COPY . /app
RUN pip3 install --no-cache-dir --root-user-action=ignore '.[all]'
# RUN playwright install
# RUN playwright install-deps
RUN apt update && \
    apt install curl -y && \
    .installer/install-litestream.sh && \
    apt remove curl -y && \
    rm -rf /var/lib/apt/lists/*
RUN mv litestream /usr/local/bin
RUN touch database.db


EXPOSE 5000

ENTRYPOINT alembic upgrade head; thoughts api run
