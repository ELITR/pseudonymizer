FROM python:3.7

# Prepare Python's venv
COPY requirements.txt /srv
COPY Makefile /srv
WORKDIR /srv
RUN make setup

# Copy app source
COPY . /srv

# Run app as standard user
RUN useradd flask && chown flask instance
USER flask

# Run target
EXPOSE 5000
HEALTHCHECK CMD curl --fail http://localhost:5000 
CMD ["./run_debug.sh"]