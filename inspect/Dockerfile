FROM python:3.7

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

COPY entry.py /inspect/

WORKDIR /inspect

CMD ["python3", "entry.py"]
