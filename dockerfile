# Base image for Python
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy dependencies
COPY Pipfile Pipfile.lock /app/

# Install Pipenv and dependencies
RUN pip install pipenv && pipenv install --system --deploy

# Copy the application code
COPY . /app

# Expose the port for the web server
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]

