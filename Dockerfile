FROM scratch AS builder

COPY requirements.txt ulozto-downloader.py ulozto-streamer.py /
COPY uldlib /uldlib/

FROM python:3.7
ENV PYTHONUNBUFFERED=1
ENV TERM=xterm

# Credits for original Dockerfile goes to: https://github.com/jansramek

RUN apt install apt-transport-https
RUN echo "deb https://deb.torproject.org/torproject.org stretch main" >> /etc/apt/sources.list
RUN echo "deb-src https://deb.torproject.org/torproject.org stretch main" >> /etc/apt/sources.list
RUN echo "deb http://ftp.de.debian.org/debian stretch main" >> /etc/apt/sources.list
RUN curl https://deb.torproject.org/torproject.org/A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89.asc | gpg --import
RUN gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | apt-key add -
RUN apt update -y
RUN apt install -y libevent*
RUN apt install -y tor deb.torproject.org-keyring
RUN pip3 install --extra-index-url https://google-coral.github.io/py-repo/ tflite_runtime

EXPOSE 8000
WORKDIR /app

VOLUME /download
VOLUME /data
ENV DOWNLOAD_FOLDER=/download
ENV DATA_FOLDER=/data
ENV DEFAULT_PARTS=10

COPY --from=builder / ./

RUN pip3 install -r requirements.txt

CMD ["./ulozto-streamer.py"]
