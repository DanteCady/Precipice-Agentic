# Use an official Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy requirements from the correct location
COPY agents/developers/developer-2/requirements.txt .
RUN pip install -r requirements.txt

# Copy the agent's code
COPY agents/developers/developer-2/ .

# Copy shared directory
COPY shared/ /app/shared/

# Expose the Developer 2 API port
EXPOSE 8002

# Run the application
CMD ["python", "app.py"]
