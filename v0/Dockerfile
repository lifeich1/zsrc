FROM debian:9 as builder

ARG BRANCH=manyuser
ARG NSBRANCH=master
ARG WORK=/root

COPY ./apt.list /etc/apt/sources.list
RUN apt-get update
RUN apt-get install -y \
    libsodium-dev \
    wget libnet1-dev \
    libpcap0.8-dev \
    build-essential

RUN wget -qO- --no-check-certificate https://github.com/ToyoDAdoubi/shadowsocksr/archive/$BRANCH.tar.gz | tar -xzf - -C /root
RUN wget -qO- --no-check-certificate https://github.com/snooda/net-speeder/archive/$NSBRANCH.tar.gz | tar -xzf - -C /root
RUN cd /root/net-speeder-$NSBRANCH && bash ./build.sh



FROM debian:9

ENV SSR_CONFPTH     /tmp/config.json

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
ARG NSBRANCH=master
ARG WORK=/root


COPY ./apt.list /etc/apt/sources.list
RUN apt-get update
RUN apt-get install -y python net-tools

RUN mkdir -p /usr/lib/x86_64-linux-gnu/pkgconfig/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libsodium.so /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libnet.so /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libpcap.so /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/pkgconfig/libsodium.pc /usr/lib/x86_64-linux-gnu/pkgconfig/
RUN ldconfig

COPY --from=builder /root/shadowsocksr-$BRANCH/shadowsocks $WORK/shadowsocksr-$BRANCH/shadowsocks/
COPY --from=builder /root/net-speeder-$NSBRANCH/net_speeder /usr/local/bin/

WORKDIR $WORK/shadowsocksr-$BRANCH/shadowsocks

COPY ./run.sh pre_run.sh


EXPOSE $SERVER_PORT
ENTRYPOINT ["bash", "pre_run.sh"]

