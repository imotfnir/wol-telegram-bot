FROM python:3.12-alpine
WORKDIR /app
COPY wol.py /app/wol.py
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
CMD ["pip" , "list python-telegram-bot"]
CMD ["/bin/sh"]
CMD ["tail", "-f", "/dev/null"]
# CMD ["python", "/app/wol.py"]

