FROM python:3.10
COPY requirements.txt main.py ./
COPY front-init/* /var/lib/www/
RUN pip install -r requirements.txt
EXPOSE 3000
ENTRYPOINT ["python", "main.py"]