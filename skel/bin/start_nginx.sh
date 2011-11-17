#!/bin/bash

WHOAMI=`whoami`
if [ "$WHOAMI" != 'root' ]
then
  echo "Must be root" 
  exit 1
fi

VIRTUAL_ENV="{{ ENVIRONMENT_DIR }}"

if [ -f "${VIRTUAL_ENV}/run/nginx.pid" ]
then
    echo "Killing Nginx: PID " `cat ${VIRTUAL_ENV}/run/nginx.pid`
    kill `cat ${VIRTUAL_ENV}/run/nginx.pid`
fi

echo "Starting Nginx..."
nginx -c ${VIRTUAL_ENV}/etc/nginx/nginx.conf >  ${VIRTUAL_ENV}/log/nginx_start.log 2>&1
echo "Started Nginx: PID " `cat ${VIRTUAL_ENV}/run/nginx.pid`
