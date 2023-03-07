import os
import json
import praw
import django
import datetime
import pytz
import time
import logging
import traceback
import google.cloud.logging

from google.cloud import secretmanager

# TODO: further abstract away the settings fetching and secrets etc
# TODO: validate that the fetching logic is sound and what we need

# setup google cloud logging handler
client = google.cloud.logging.Client()
client.setup_logging()


def fetch_secret(secret_id):
    '''
    This utility function returns a secret payload at runtime using the secure google secrets API 
    '''
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/mhs-reddit/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode('UTF-8')


def main():
    '''
    This pseudocode describes the main loop function of the Gather bot.  

    now = now()

    FROM toxit_inference_task table as job
        fetch most recent record
            WHERE start_sched > now AND status == 0

                if None job wait 10 seconds and loop

    if job exists start inference task on job
        set job.status == 1

        if inference task succeeds
            set job.status = 2 and loop

        if inference task fails
            set job.status = 3 and loop


    '''

    # copying how manage.py does it for some reason we must import the libs here and not at the top
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    django.setup()
    from Task_Manager import Task_Manager
    from gather.models import Inference_task

    logging.info("Starting Task Manager...")
    task_manager = Task_Manager()
    while True:
        # fetch and construct praw object
        praw_obj = praw.Reddit(
            client_id=fetch_secret('praw_client_id'),
            client_secret=fetch_secret('praw_client_secret'),
            password=fetch_secret('praw_client_password'),
            user_agent=fetch_secret('praw_user_agent'),
            username=fetch_secret('praw_user_name'),
        )

        # set readonly mode
        praw_obj.read_only = False

        # when is now?
        now = datetime.datetime.now(pytz.timezone('America/Regina'))

        # try to fetch a task from the database
        task = Inference_task.objects.filter(
            start_sched__lte=now, status=0).first()
        if task == None:
            logging.debug('Task Manager is Idle...')
            time.sleep(10)
            continue
        logging.info(f"Starting task: {task}")
        task.status = 1
        task.save()
        try:
            task_manager.do_Task(task, fetch_secret(
                'mhs_api_url'), fetch_secret('mhs_api_key'), praw_obj)
        except:
            logging.error(f"UNABLE TO COMPLETE: {task}")
            logging.error(traceback.format_exc())
            task.status = 3
            task.save()
            continue
        # at this point in the code we have a job object, do we want to do anything with it?
        logging.info(f"Completed task: {task}")
        task.status = 2
        task.save()


if __name__ == '__main__':
    main()
