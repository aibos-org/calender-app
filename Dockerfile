# Use the official Python base image
FROM python:3.9

ENV  FLASK_RUN_PORT=5000
# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code to the container
COPY . .

# Expose the port on which the Flask app will run
EXPOSE 80


# Set the entrypoint command to run the Flask app
CMD ["python", "app.py"]