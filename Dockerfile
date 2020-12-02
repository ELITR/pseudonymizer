FROM python:3.8

# Prepare Python's venv
COPY requirements.txt /srv
COPY Makefile /srv
WORKDIR /srv
RUN make build

# Copy app source
COPY . /srv

# Run target
EXPOSE 5000
CMD ["make", "run"]