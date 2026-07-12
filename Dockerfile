FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# git is required at runtime — gitpython shells out to the git binary
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Create a non-privileged user to run the app
RUN adduser --disabled-password --gecos "" agentuser

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY src/script.py src/chatWithModel.py ./
# We copy a default config, but we'll override it with a volume in Compose
COPY config.yaml .

# Install the `news` wrapper on PATH so `docker exec news-agent news trigger` works
COPY scripts/news /usr/local/bin/news
RUN chmod +x /usr/local/bin/news

# Create the news repo working dir and hand both it and the app to our user.
# A named volume mounted at /data/news inherits this ownership on first use.
RUN mkdir -p /data/news \
    && chown -R agentuser:agentuser /app /data

# Switch to the non-privileged user
USER agentuser

# The command to run when the container starts
ENTRYPOINT ["python", "script.py"]