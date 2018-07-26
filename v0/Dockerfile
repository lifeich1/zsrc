FROM debian:9

ENV SSR_CONFPTH     /tmp/config.json
ENV PRE_RUNSH       _run.sh

ENV SERVER_ADDR     0.0.0.0
ENV SERVER_PORT     443
ENV PASSWORD        psw
ENV METHOD          aes-128-ctr
ENV PROTOCOL        auth_aes128_md5
ENV PROTOCOLPARAM   32
ENV OBFS            tls1.2_ticket_auth_compatible
ENV TIMEOUT         300
ENV DNS_ADDR        8.8.8.8
ENV DNS_ADDR_2      8.8.4.4

ARG BRANCH=manyuser
ARG WORK=~


COPY ./apt.list /etc/apt/sources.list
RUN apt-get update
RUN apt-get install -y python \
    libsodium-dev \
    wget


RUN mkdir -p $WORK && \
    wget -qO- --no-check-certificate https://github.com/ToyoDAdoubi/shadowsocksr/archive/$BRANCH.tar.gz | tar -xzf - -C $WORK


WORKDIR $WORK/shadowsocksr-$BRANCH/shadowsocks

COPY ./run.sh $PRE_RUNSH


EXPOSE $SERVER_PORT
CMD bash $PRE_RUNSH

