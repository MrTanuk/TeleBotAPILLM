FROM python:3.11-slim

WORKDIR /workspace

# The dependecies essential to run the bot
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /workspace/src/

ENV PYTHONPATH=/workspace/src

CMD ["python", "-m" , "telegram_bot.main"]
