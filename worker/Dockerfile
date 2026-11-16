FROM python:3.11.18-slim-trixie
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker.py db.py ./

RUN useradd --system --uid 10001 app
USER 10001

CMD ["python", "worker.py"]
