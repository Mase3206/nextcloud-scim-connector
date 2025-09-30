FROM python:3.13-slim

# Update system and install ping and curl
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y iputils-ping curl

# Set the working directory
WORKDIR /opt/nc_scim

# Install nc_scim (built by Poetry) and all its dependencies
COPY ./dist/nc_scim*.whl .
RUN pip install *.whl && \
    rm -rf *.whl

# Copy nc_scim source
COPY ./src/nc_scim/* .

# Remove pycache files that may have been copied over
RUN find . -name "*.pyc" -delete && \
    find . -name "__pycache__" -type d -delete

# Expose 8000, which is used by FastAPI
EXPOSE 8000

# Start the thang
CMD ["python", "-m", "fastapi", "run", "receiver.py"]
