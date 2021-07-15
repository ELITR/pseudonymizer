FROM python:3.7

# Configurate image
RUN useradd -u 999 psan_user && apt update && apt upgrade -y && apt install -y uwsgi uwsgi-plugin-python3 wait-for-it

# Setup app
COPY requirements.txt Makefile /srv/
WORKDIR /srv
RUN make setup 

# Copy app source
COPY . /srv
RUN chown psan_user instance

# Run target
EXPOSE 5000
HEALTHCHECK CMD curl --fail http://localhost:5000 
CMD ["./run.sh"]