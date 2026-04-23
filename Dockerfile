FROM python:3.12.13-trixie

LABEL author="MCPanel by Miles Muehlbach and Yabo Wang"

WORKDIR /app

COPY . .
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN uv sync --locked
RUN apt-get update && apt-get install -y curl nodejs npm

RUN npm install && npm run build

EXPOSE 8080

CMD ["uv", "run", "python", "main.py"]