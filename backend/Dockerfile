FROM python:3.9-slim

WORKDIR /app

COPY [requirements.txt](http://_vscodecontentref_/1) .
RUN pip install --no-cache-dir -r [requirements.txt](http://_vscodecontentref_/2)

COPY . .

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]