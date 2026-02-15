# Dockerfile for running Miss Hinata Bot
# This image is suitable for deployment on Koyeb or any container platform.

FROM python:3.11-slim

# create non-root user to run the bot (optional but recommended)
RUN useradd --create-home appuser
WORKDIR /home/appuser

# copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# copy application code
COPY . ./

# set the working directory for runtime
WORKDIR /home/appuser

# make sure database is persisted outside the container if using volumes
VOLUME ["/home/appuser/data.db"]

# environment variables recommendation
ENV PYTHONUNBUFFERED=1

# run the bot
USER appuser
CMD ["python", "main.py"]
