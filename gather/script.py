import json
import praw
import sys
import os
import django
import datetime
import pytz
import numpy
import itertools

sys.path.append('/home/kyllo/projects/gather_bot/gather')
os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'
django.setup()

from gather.models import *
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

# make a dummy edges json
edges = {}

# These are helpers for pushing to the database

def push_Subreddit(sub_object):
    custom_id  = sub_object.info()['pk']
    display_name = sub_object.info()['display_name']
    r = Subreddit(custom_id=custom_id, display_name=display_name)
    r.save()
    return r

def push_Subreddit_result(sub_object, edges_json, subreddit, inference_task):
    min = subreddit.stats()['min']
    max = subreddit.stats()['max']
    mean = subreddit.stats()['mean']
    std = subreddit.stats()['std']
    timestamp = subreddit.stats()['timestamp']
    edges = edges_json
    r = Subreddit_result(   subreddit=subreddit, 
                            inference_task=inference_task, 
                            min_result=min, 
                            max_result=max, 
                            mean_result=mean, 
                            std_result=std, 
                            timestamp=timestamp,
                            edges=edges )
    r.save()
    return r

def push_Subreddit_mod(sub_object, subreddit, result):
    for mod in sub_object.mod_set():
        r = Subreddit_mod(subreddit=subreddit, username=mod, subreddit_result=result)
        r.save()

def push_Comment_result(sub_object, subreddit, result):
    for comment in sub_object.data():
        subreddit_result = result
        subreddit = subreddit
        permalink = comment['permalink']
        mhs_score = comment['mhs_score']
        comment_body = comment['comment_body']
        username = comment['username']
        r = Comment_result( subreddit_result=result, 
                            subreddit=subreddit, 
                            permalink=permalink, 
                            mhs_score=mhs_score, 
                            comment_body=comment_body, 
                            username=username )                              
        r.save()

def push_Gather(sub_object, edges, task):
    s = push_Subreddit(sub_object)
    r = push_Subreddit_result(sub_object, edges, s, task )
    push_Subreddit_mod(sub_object, s, r)
    push_Comment_result(sub_object, s, r )

# these are helpers for set similarity
def set_intersect_card(A, B):
    return len(A.intersection(B))

def set_union_card(A, B):
    return len(A.union(B))

# this is the one that sucked to write
def build_json_edges(gather_list, context):
    wrapper = {context:{}}
    outer = []
    
    for i in range(len(gather_list)):
        inner = {}
        for j in range(i+1, len(gather_list)):
            
            if context == 'mods':
                A = gather_list[i].mod_set()
                B = gather_list[j].mod_set()
                intersect = A.intersection(B)
                cardinality = len(intersect)
                if cardinality > 0:
                    data = { gather_list[j].name():cardinality}
                    inner.update(data)
            
            if context == 'authors':
                A = gather_list[i].author_set()
                B = gather_list[j].author_set()
                intersect = A.intersection(B)
                cardinality = len(intersect)
                if cardinality > 0:
                    data = { gather_list[j].name():cardinality}
                    inner.update(data)
        
        outer.append(inner)
    for (i, chunk) in zip(gather_list, outer):
        item = {i.name():chunk}
        wrapper[context].update(item)
    return wrapper


##START SRIPT##

# fetch a list of subreddits
SUBS_N = 50

# when is now in regina
now = datetime.datetime.now(pytz.timezone('America/Regina'))

# make an empty lists
sub_list = []

for subreddit in reddit.subreddits.popular(limit=SUBS_N):
    sub_list.append(subreddit.display_name)

# create a dummy inference task for testing
task = Inference_task(      start_sched=now,
                            time_scale = 'week',
                            min_words=1,
                            forest_width=1,
                            per_post_n=1000,
                            comments_n=500,
                            subreddit_set=sub_list,
                            status='0',                          
                            
                            )
task.save()

# fetch the dummy task record using a simplistic method 'latest'
task = Inference_task.objects.latest('start_sched')

# pass the task to the Task manager class object to construct the Gather list
gathers = Task_manager(task, api_url, api_key, reddit)

# fetch the list of gather objects
mylist = gathers.gather_list()