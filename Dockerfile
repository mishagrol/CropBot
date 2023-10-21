# FROM python:3.7.17
FROM python:3.9.16-slim-bullseye
WORKDIR /home/src
COPY requirements.txt .
RUN  pip3 install -r requirements.txt
ENV LANG ru_RU.UTF-8
ENV LC_ALL ru_RU.UTF-8

CMD ["python3.9",  "bot.py"]
