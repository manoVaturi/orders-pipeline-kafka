FROM python:3.11.18-slim-trixie
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --system --uid 10001 app
USER 10001

EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0"]
