FROM python:3.12

WORKDIR /app

COPY . /app

VOLUME /app/storage

EXPOSE 5000
EXPOSE 3000

CMD ["python", "./main.py"]