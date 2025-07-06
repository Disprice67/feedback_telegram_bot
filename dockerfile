FROM python:3.11-slim

WORKDIR /usr/app/src/

COPY req.txt ./
RUN pip install --no-cache-dir -r req.txt

COPY . /usr/app/src/

EXPOSE 8080

CMD ["python", "main.py"]
