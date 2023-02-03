import os
import json
import praw
import sys
import django
import datetime
import pytz
import random

sys.path.append('/home/kyllo/projects/gather_bot/gather')
os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'
django.setup()

from gather.models import Subreddit, Inference_task, Subreddit_result, Subreddit_mod, Comment_result
from classes import Gather, Task_manager


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
    client_id = keys['client_id'],
    client_secret = keys['client_secret'],
    password = keys['password'],
    user_agent="web:mhs-crawler-bot:v1 (by /u/mhs-crawler-bot)",
    username="mhs-crawler-bot",
)

# set readonly mode
reddit.read_only = False

# when is now in regina
now = datetime.datetime.now(pytz.timezone('America/Regina'))

# #fetch a list of subreddits
# SUBS_N = 1

# # make an empty list
# biglist = []

# # fetch all the subreddits you can
# for subreddit in reddit.subreddits.popular(limit=None):
#     biglist.append(subreddit.display_name)

# # build a random nonrepeating sample of the list
# sublist = random.sample(biglist, SUBS_N)

# sublist = ['rpcs3', 'BingQuizAnswers', 'subnautica']
sublist = ['programming','rpcs3', 'subnautica']


# create a dummy inference task for testing and push to db
task_out = Inference_task(      start_sched=now,
                                time_scale = 'week',
                                min_words=1,
                                forest_width=1,
                                per_post_n=1000,
                                comments_n=100,
                                subreddit_set=sublist,
                                status='0',                          
                            
                            )
task_out.save()

# fetch the dummy task record from db using a simplistic method 'latest'
task_in = Inference_task.objects.latest('start_sched')

# pass the task to the Task manager class object to construct the Gather list
gathers = Task_manager(task_in, api_url, api_key, reddit)
