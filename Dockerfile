FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV GEMINI_API_KEY=${GEMINI_API_KEY}
ENV PINECONE_API_KEY=${PINECONE_API_KEY}
ENV PINECONE_INDEX=${PINECONE_INDEX:-skincare-agent}
ENV GEMINI_MODEL=${GEMINI_MODEL:-gemini-3.6-flash}
ENV GEMINI_FALLBACK_MODEL=${GEMINI_FALLBACK_MODEL:-gemini-2.0-flash}

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
