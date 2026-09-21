FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python generate_evals.py

ENV GEMINI_API_KEY=${GEMINI_API_KEY}
ENV PINECONE_API_KEY=${PINECONE_API_KEY}
ENV PINECONE_INDEX=${PINECONE_INDEX:-skincare-agent}

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
