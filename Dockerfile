FROM python:3.11-slim

LABEL maintainer="Rondinelli Castilho (N0rd)"
LABEL description="Shell Matrix - Advanced Terminal Dashboard"

WORKDIR /app

RUN apt-get update && apt-get install -y \
    bash \
    zsh \
    fish \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shell_matrix.py .

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["python", "shell_matrix_clean.py"]
