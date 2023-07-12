FROM python:3


WORKDIR /app


COPY requirements.txt .
RUN pip install -r requirements.txt uvicorn[standard]

COPY . .
CMD ["gunicorn", "main:app", "-b", "0.0.0.0:8080", "-k", "uvicorn.workers.UvicornWorker"]
