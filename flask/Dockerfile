FROM python:3.7

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

COPY config.yaml /flask/
COPY flask-entry.py /flask/
COPY gunicorn.conf.py /flask/
COPY githubutil /flask/githubutil/

WORKDIR /flask

CMD ["gunicorn", "flask-entry:app", "-c", "./gunicorn.conf.py"]
