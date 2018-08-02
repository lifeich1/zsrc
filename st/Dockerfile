FROM debian:9

ENV HOME=/root

COPY ./apt.list /etc/apt/sources.list

RUN apt-get update
RUN apt-get install -y wget


WORKDIR $HOME

RUN wget https://github.com/syncthing/syncthing/releases/download/v0.14.49/syncthing-linux-amd64-v0.14.49.tar.gz -O sync.tar.gz
RUN tar zxvf sync.tar.gz
RUN mv `ls | grep syncthing-linux-amd64` sync
RUN cp sync/syncthing /usr/bin/
RUN rm -rf sync

EXPOSE 8384
EXPOSE 22000
EXPOSE 21027/udp

CMD syncthing -no-browser -gui-address=0.0.0.0:8384
