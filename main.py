import os
import json
import praw
import django
import datetime
import pytz
import time

#TODO: further abstract away the settings fetching and secrets etc
#TODO: incorporate into testing scripts
#TODO: validate that the fetching logic is sound and what we need
#TODO: add proper logging
#TODO: add graceful shutdown

#TESTS:
# - picks up task scheduled for now - PASS
# - picks up task scheduled in past and executes immediately - PASS
# - picks up task scheduled in future - PASS
# - assigns proper status to tasks for each execution for each case

                    # ('0', 'Scheduled'), - PASS
                    # ('1', 'In Progress'), - 
                    # ('2', 'Completed'), - PASS
                    # ('3', 'Error'), - 
                    # ('4', 'Cancelled') - 
def main():
    '''
    This pseudo describes the main loop function of the Gather bot.  
    
    now = now()

    FROM toxit_inference_task table as job
        fetch most recent record
            WHERE start_sched > now AND status == 0

                if None job wait 10 seconds and loop

    if job exists start inference task on job
        set job.status == 1

        if inference task succeeds
            set job.status = 2

        if inference task fails
            set job.status = 3

    '''
    # copying how manage.py does it
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    django.setup()
    from Task_Manager import Task_Manager
    from gather.models import Inference_task

    # fetch the secrets from the keyfile
    keysJSON = open('keys.json')
    open_file = keysJSON.read()
    model_attribs = json.loads(open_file)['model']
    keys = json.loads(open_file)['reddit']
    keysJSON.close()

    # setup api connection variables
    api_key = model_attribs['apikey']
    api_url = "https://kyllobrooks.com/api/mhs"

    # status message, replace with logging
    print("Starting Task Manager...")

    while True:

        # fetch and construct praw object
        praw_obj = praw.Reddit(
            client_id = keys['client_id'],
            client_secret = keys['client_secret'],
            password = keys['password'],
            user_agent="web:mhs-crawler-bot:v1 (by /u/mhs-crawler-bot)",
            username="mhs-crawler-bot",
            )

        # set readonly mode
        praw_obj.read_only = False
        
        # when is now?
        now = datetime.datetime.now(pytz.timezone('America/Regina'))        

        # try to fetch a task from the database
        task = Inference_task.objects.filter(start_sched__lte=now, status=0).first()
        if task == None:
            # debug message, dont log this
            print('Task Manager is Idle...')
            time.sleep(10)
            continue
        # log this
        task.status = 1
        task.save()
        try:
            job = Task_Manager(task, api_url, api_key, praw_obj)
        except:
            # log this
            task.status = 3
            task.save()
            continue
        # at this point in the code we have a job object, do we want to do anything with it?
        # log this
        task.status = 2
        task.save()

  
if __name__ == '__main__':
    main()