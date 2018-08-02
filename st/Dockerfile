FROM debian:9 as builder

COPY ./apt.list /etc/apt/sources.list
RUN apt-get update \
    && apt-get install -y wget \
    && cd /root \
    && wget https://github.com/syncthing/syncthing/releases/download/v0.14.49/syncthing-linux-amd64-v0.14.49.tar.gz -O sync.tar.gz \
    && tar zxvf sync.tar.gz \
    && mv `ls | grep syncthing-linux-amd64` sync


FROM debian:9

COPY --from=builder /root/sync/syncthing /usr/bin/

EXPOSE 8384
EXPOSE 22000
EXPOSE 21027/udp

CMD syncthing -no-browser -gui-address=0.0.0.0:8384
