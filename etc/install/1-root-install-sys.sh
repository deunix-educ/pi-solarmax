#!/bin/bash
if [ $EUID -ne 0 ]; then
  echo "Lancer en root: # $0" 1>&2
  exit 1
fi
apt update
#apt upgrade

apt install build-essential binutils supervisor

# supervisor http access
if [ ! -e "/etc/supervisor/supervisord.conf.old" ]; then
    cp /etc/supervisor/supervisord.conf /etc/supervisor/supervisord.conf.old
    cat >> /etc/supervisor/supervisord.conf << EOF
    [inet_http_server]
    port = *:9001
    username = root
    password = toor
    EOF
fi

apt install python3-dev python3-pip python3-venv

#python3-paho-mqtt python3-pyaml

