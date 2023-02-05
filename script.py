import os
import json
import praw
import django
import datetime
import pytz

# copying how manage.py does it

#  at present this script is a hacky way to do tests
#  we need to make these more formalized and structured into the tests.py file

def main():
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

    # fetch and construct praw object
    reddit = praw.Reddit(
        client_id=keys['client_id'],
        client_secret=keys['client_secret'],
        password=keys['password'],
        user_agent="web:mhs-crawler-bot:v1 (by /u/mhs-crawler-bot)",
        username="mhs-crawler-bot",
    )

    # set readonly mode
    reddit.read_only = False

    # when is now in regina
    now = datetime.datetime.now(pytz.timezone('America/Regina'))
    future = now + datetime.timedelta(minutes=5)
    past = now - datetime.timedelta(minutes=5)

    # #fetch a list of subreddits
    # SUBS_N = 1

    # # make an empty list
    # biglist = []

    # # fetch all the subreddits you can
    # for subreddit in reddit.subreddits.popular(limit=None):
    #     biglist.append(subreddit.display_name)

    # # build a random nonrepeating sample of the list
    # sublist = random.sample(biglist, SUBS_N)

    sublist = ['programming', 'rpcs3', 'subnautica']

    # create a dummy inference task for testing and push to db
    task_out = Inference_task(start_sched=now,
                              time_scale='week',
                              min_words=1,
                              forest_width=1,
                              per_post_n=1000,
                              comments_n=100,
                              subreddit_set=sublist,
                              status='0',

                              )
    task_out.save()

        # create a dummy inference task for testing and push to db
    task_out = Inference_task(start_sched=past,
                              time_scale='week',
                              min_words=1,
                              forest_width=1,
                              per_post_n=1000,
                              comments_n=100,
                              subreddit_set=sublist,
                              status='0',

                              )
    task_out.save()

        # create a dummy inference task for testing and push to db
    task_out = Inference_task(start_sched=future,
                              time_scale='week',
                              min_words=1,
                              forest_width=1,
                              per_post_n=1000,
                              comments_n=100,
                              subreddit_set=sublist,
                              status='0',

                              )
    task_out.save()



if __name__ == '__main__':
    main()
