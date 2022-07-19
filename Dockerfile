FROM python:3.10-alpine

ENV PYTHONPYCACHEPREFIX=/tmp

WORKDIR /to-do-list-v2-backend
RUN pip install virtualenv
RUN virtualenv venv
RUN source venv/bin/activate
EXPOSE 9999
COPY . .
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "/to-do-list-v2-backend/src/main.py"]
