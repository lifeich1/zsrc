#!/bin/sh

SSR_PORT=2333

cat > /root/config.json << END
{
    "server": "0.0.0.0",
    "server_ipv6": "::",
    "server_port": 2333,
    "local_address": "127.0.0.1",
    "local_port": 1080,

    "password": "pwd",
    "method": "chacha20",
    "protocol": "auth_aes128_sha1",
    "protocol_param": "20",
    "obfs": "tls1.2_ticket_auth",
    "obfs_param": "",
    "speed_limit_per_con": 0,
    "speed_limit_per_user": 0,

    "additional_ports" : {}, // only works under multi-user mode
    "timeout": 120,
    "udp_timeout": 60,
    "dns_ipv6": false,
    "connect_verbose_info": 0,
    "redirect": "",
    "fast_open": false
}
END

docker run -itd --name ssr -p $SSR_PORT:2333 \
    -v /root/config.json:/tmp/config.json \
    lintd/ssr

echo 
echo '[done]'
