FROM python:3.9

WORKDIR /app

COPY requirements.txt ./
COPY main.py ./

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 3000

CMD ["python", "main.py"]