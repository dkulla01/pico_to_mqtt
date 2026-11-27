FROM python:3.15-trixie AS builder

RUN pip install poetry==2.5.2

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN touch README.md
RUN echo "I am a placeholder readme to make poetry happy" > README.md

RUN poetry install --without dev --no-root && rm -rf ${POETRY_CACHE_DIR}


FROM python:3.15-slim-trixie AS runtime

WORKDIR /app
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY src/pico_to_mqtt ./pico_to_mqtt

ENTRYPOINT [ "python", "-m", "pico_to_mqtt.main" ]
