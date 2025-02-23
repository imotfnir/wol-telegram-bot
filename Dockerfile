FROM python:3.12-alpine
WORKDIR /app
COPY wol.py /app/wol.py
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "/app/wol.py"]
# CMD ["tail", "-f", "/dev/null"]

