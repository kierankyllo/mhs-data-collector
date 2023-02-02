import os
#DONT INCLUDE THIS IN THE .PY FILE
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import json
import praw
import sys
import django
import datetime
import pytz
import numpy
import itertools

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

class Task_manager():
    '''
    '''
    def __init__(self, task_object, api_url, api_key, praw_object, chunk_size=100):
        # private parameter members
        self.__task = task_object
        self.__subreddit_set = self.__task.subreddit_set
        self.__pk = self.__task.pk
        self.__url = api_url
        self.__apikey = api_key
        self.__praw = praw_object
        self.__chunk_size = chunk_size
        self.__Gather_list = []
        self.__subreddit_list = []
        # constructors
        self.__build_Gather_lists()
        self.__dims = len(self.__Gather_list)
        self.__edges_list = self.__wrap_JSON_edges()
        self.__push_All()
    
    # defines a function to build a list of Gather objects
    def __build_Gather_lists(self):
        for sub in self.__subreddit_set:            
            sample = Gather(sub, self.__url, self.__apikey, self.__praw,    scope=self.__task.time_scale, 
                                                                            min_words=self.__task.min_words, 
                                                                            inference=True, 
                                                                            forest_width=self.__task.forest_width, 
                                                                            per_post_n=self.__task.per_post_n, 
                                                                            comments_n=self.__task.comments_n, 
                                                                            chunk_size=self.__chunk_size
                                                        )
            self.__Gather_list.append(sample)
            self.__subreddit_list.append(sample.name)
    
    # this sucked to write i need a whiteboard to explain it
    def __discover_JSON_edges(self, context):
        outer = []

        for i in range(self.__dims):
            inner = {}
            for j in range(i+1, self.__dims):
                
                if context == 'mods':
                    A = self.__Gather_list[i].mod_set()
                    B = self.__Gather_list[j].mod_set()
                    intersect = A.intersection(B)
                    cardinality = len(intersect)
                    if cardinality > 0:
                        data = { self.__Gather_list[j].name():cardinality}
                        inner.update(data)
                
                if context == 'authors':
                    A = self.__Gather_list[i].author_set()
                    B = self.__Gather_list[j].author_set()
                    intersect = A.intersection(B)
                    cardinality = len(intersect)
                    if cardinality > 0:
                        data = {self.__Gather_list[j].name():cardinality}
                        inner.update(data)
            
            outer.append(inner)
    
        return outer

    def __wrap_JSON_edges(self):
        mods_edges = self.__discover_JSON_edges('mods')
        authors_edges = self.__discover_JSON_edges('authors')
        wrapper = []
        for (m, a) in zip (mods_edges, authors_edges):
            data = {"mods":m , "authors":a}
            wrapper.append(data)
        return wrapper
    
    def __push_Subreddit(self, sub_object):
        custom_id  = sub_object.info()['pk']
        display_name = sub_object.info()['display_name']
        r = Subreddit(custom_id=custom_id, display_name=display_name)
        r.save()
        return r

    def __push_Subreddit_result(self, sub_object, edges_json, subreddit, inference_task):
        min = sub_object.stats()['min']
        max = sub_object.stats()['max']
        mean = sub_object.stats()['mean']
        std = sub_object.stats()['std']
        timestamp = sub_object.stats()['timestamp']
        edges = edges_json
        r = Subreddit_result(   subreddit=subreddit, 
                                inference_task=inference_task, 
                                min_result=min, 
                                max_result=max, 
                                mean_result=mean, 
                                std_result=std, 
                                timestamp=timestamp,
                                edges=json.dumps(edges))
        r.save()
        return r

    def __push_Subreddit_mod(self, sub_object, subreddit, result):
        for mod in sub_object.mod_set():
            r = Subreddit_mod(subreddit=subreddit, username=mod, subreddit_result=result)
            r.save()

    def __push_Comment_result(self, sub_object, subreddit, result):
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

    def __push_Gather(self, sub_object, edges, task):
        s = self.__push_Subreddit(sub_object)
        r = self.__push_Subreddit_result(sub_object, edges, s, task )
        self.__push_Subreddit_mod(sub_object, s, r)
        self.__push_Comment_result(sub_object, s, r )

    def __push_All(self):
        for (gather, edge) in zip(self.__Gather_list, self.__edges_list):
            self.__push_Gather(gather, edge, self.__task)
        print('All Data Pushed to Tables')

    # accessor functions
    def gather_list(self):
        return self.__Gather_list
    
    def edges_list(self):
        return self.__edges_list

# fetch a list of subreddits
SUBS_N = 100

# when is now in regina
now = datetime.datetime.now(pytz.timezone('America/Regina'))

# make an empty lists
sub_list = []

for subreddit in reddit.subreddits.popular(limit=SUBS_N):
    sub_list.append(subreddit.display_name)

# create a dummy inference task for testing and push to db
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
