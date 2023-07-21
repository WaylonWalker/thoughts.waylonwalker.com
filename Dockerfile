from python:3.11

WORKDIR /app
Copy pyproject.toml /app
COPY thoughts/__about__.py /app/thoughts/__about__.py
COPY README.md /app
RUN pip3 install '.[all]'
COPY . /app
RUN pip3 install '.[all]'

EXPOSE 5000

# ENTRYPOINT alembic upgrade head; thoughts api run
ENTRYPOINT thoughts api run
