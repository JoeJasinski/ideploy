#!/bin/sh
. {{ ENVIRONMENT_DIR }}/bin/activate

MAIN_MODULE="{{ APP_NAME }}"
ENV_SETTINGS="{{ APP_NAME }}.settings"
PID_FILE="${VIRTUAL_ENV}/run/fcgi.pid"
OUTLOG_FILE="${VIRTUAL_ENV}/log/fcgi_out.log"
ERRLOG_FILE="${VIRTUAL_ENV}/log/fcgi_err.log"
SOCKET_FILE="${VIRTUAL_ENV}/run/django.socket"
export PYTHONPATH="$PYTHONPATH:${VIRTUAL_ENV}/proj/:${VIRTUAL_ENV}/proj/${MAIN_MODULE}/"

if [ -f "$PID_FILE" ]
then
    echo "Killing FCGI: PID " `cat ${PID_FILE}`
    kill `cat ${PID_FILE}`
fi

echo "Starting FCGI..."
env python ${VIRTUAL_ENV}/bin/django-admin.py runfcgi --settings=${ENV_SETTINGS} \
           deamonize=true socket=${SOCKET_FILE} \
           method=prefork outlog=${OUTLOG_FILE}  errlog=${ERRLOG_FILE} \
           pidfile=${PID_FILE} umask=0002
echo "Started FCGI: PID " `cat ${PID_FILE}`
