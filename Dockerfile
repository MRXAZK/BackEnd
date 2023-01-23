FROM python:3.11-slim-buster

# Install tesseract
RUN apt-get update && apt-get install -y tesseract-ocr libtesseract-dev tesseract-ocr-script-latn libgl1

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose the port for the application
EXPOSE 8000

# Start the application
CMD ["uvicorn", "app.main:app", "--port", "80"]
