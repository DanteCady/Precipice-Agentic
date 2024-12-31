# Use full Python image instead of slim
FROM python:3.10

# Set the working directory
WORKDIR /app

# Install PostgreSQL client and build dependencies
RUN apt-get update \
    && apt-get install -y \
        postgresql-server-dev-15 \
        postgresql-client-15 \
        gcc \
        python3-dev \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from the correct location
COPY agents/boss/requirements.txt .

# Install psycopg2 from source instead of binary
RUN pip uninstall -y psycopg2-binary psycopg2 && \
    pip install --no-cache-dir psycopg2==2.9.9

# Install other requirements
RUN pip install -r requirements.txt

# Copy the agent's code
COPY agents/boss/ .

# Copy shared directory
COPY shared/ /app/shared/

# Expose the Boss API port
EXPOSE 8000

# Run the application
CMD ["python", "app.py"]
