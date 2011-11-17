. {{ ENVIRONMENT_DIR }}/bin/activate

ENV_NAME="p2p"
MAIN_MODULE="birdflew"
ENV_SETTINGS="birdflew.settings"
export PYTHONPATH="$PYTHONPATH:${VIRTUAL_ENV}/proj/:${VIRTUAL_ENV}/proj/${MAIN_MODULE}/"

echo "Starting Client..."
env python ${VIRTUAL_ENV}/bin/django-admin.py bf_run_client --settings=${ENV_SETTINGS} > ${VIRTUAL_ENV}/log/twisted_service.log 2>&1 & 
echo "Started Client:  " 
