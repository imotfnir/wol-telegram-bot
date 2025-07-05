FROM python:3.13-alpine
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY wol.py /app/wol.py
CMD ["python", "/app/wol.py"]
# CMD ["tail", "-f", "/dev/null"]

