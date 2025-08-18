FROM python:3.11-slim

WORKDIR /app

# System deps (fonts for reportlab PDFs)
RUN apt-get update && apt-get install -y --no-install-recommends     libfreetype6 libjpeg62-turbo liblcms2-2 libtiff6 ghostscript     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]
