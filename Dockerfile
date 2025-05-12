# Base image
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file
COPY app/themovie/requirements.txt .

# Install the requirements
RUN pip install --no-cache-dir -r requirements.txt
# Copy the whole FastAPI app
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Command to run the app
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "app.themovie.main:app", "--bind", "0.0.0.0:8000", "--timeout", "0", "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-"]
