FROM python:3.7-alpine
COPY . /action
WORKDIR /action
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["/action/action.py"]