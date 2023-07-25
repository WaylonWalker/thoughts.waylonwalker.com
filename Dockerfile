FROM python:3.11

WORKDIR /app
COPY pyproject.toml /app
COPY thoughts/__about__.py /app/thoughts/__about__.py
COPY README.md /app
RUN pip3 install '.[all]'
RUN pip3 install datasette
COPY . /app
RUN pip3 install '.[all]'

EXPOSE 5000

ENTRYPOINT alembic upgrade head; thoughts api run
# CMD /app/gross.sh
# CMD thoughts api run
