FROM python:3.14-rc-alpine3.21
WORKDIR /app
COPY wol.py /app/wol.py
CMD ["python", "/app/wol.py"]
