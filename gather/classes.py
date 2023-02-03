import praw
import json
import numpy as np
import requests
from tqdm import tqdm
import datetime
import re
import itertools
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

from gather.models import Subreddit, Inference_task, Subreddit_result, Subreddit_mod, Comment_result

#TODO: debug using 'issues' workflow
#TODO: build test scripts for the class
#TODO: add error handling code
#TODO: move 


class Gather:
    """
    Class object representing a subreddit
    Keyword arguments:
    display_name -- str - required, the display name of the subreddit
    url -- str - required, the url of the api endpoint for inference
    apikey -- str - required, the aipkey for the endpoint
    praw_object -- object - required, the praw reddit object
    scope -- str - defaults to 'week', sets the scope of collection ['hour', 'day', 'week', 'month', 'year', 'all']
    min_words -- int - defaults to 20, the minimum words to collect as a comment
    inference -- bool - defaults to True, build with inference or not
    forest_width -- int - defaults to 10, the number of 'more comments' to traverse in the comment forest
    per_post_n -- int - default to 100, the max number of comments to gather from a single post
    comments_n -- int - defaults to 1000, the max number of comments in total to gather
    chunk_size -- int - defaults to 100, the number of samples to infer in each request to the api
    """
    # defines a constructor
    def __init__(self, display_name, url, apikey, praw_object, scope='week', min_words=20, inference=True, forest_width=10, per_post_n=100, comments_n=1000, chunk_size=100):
        # private parameter members
        self.__scope = scope
        self.__min_words = min_words
        self.__name = display_name
        self.__url = url
        self.__apikey = apikey
        self.__forest_width = forest_width
        self.__per_post_n = per_post_n
        self.__comments_n = comments_n
        self.__chunksize = chunk_size
        # private 
        self.__sub = praw_object.subreddit(display_name)
        self.__posts = self.__sub.top(time_filter=self.__scope, limit=None)
        self.__stats = {}
        self.__data = []
        self.__mod_set = set()
        self.__author_set = set()        
        self.__sample_list = []        
        self.__nested_results_list = []   
        self.__results = []
        # info dictionary maps to 'Subreddit' ORM
        self.__info = {
            'pk' : self.__sub.id,
            'display_name' : display_name,
        }
        # task dictionary maps to 'Inference_Task' ORM
        self.__task = {
            'time_scale' : scope,
            'min_words' : min_words,
            'forest_width' : forest_width,
            'per_post_n' : per_post_n,
            'comments_n' : comments_n,
        }      
        # constructors and sanitizers
        self.__fetch_mods()
        self.__fetch_content()
        self.__parse_data()
        if inference == True:          
            self.__get_mhs_ratings(self.__chunksize)
            self.__results = self.__flatten_results(self.__nested_results_list)
            self.__results = list(self.__results)
            self.__append_results_data()
            self.__build_stats()

    # constructor function to build moderator list
    def __fetch_mods(self):
        for mod in self.__sub.moderator():
            self.__mod_set.add(mod.name)

    # constructor function to build comments list
    def __fetch_content(self):
        t = tqdm(total=self.__comments_n, desc='Collection: '+ self.__name)
        post_tick = 0
        for post in self.__posts:      
            post.comments.replace_more(limit=self.__forest_width)
            comments = post.comments.list()
            comment_tick = 0
            for comment in comments:
                if comment_tick >= self.__per_post_n: 
                    break
                if comment.author is not None and self.__count_words(comment.body) > self.__min_words:
                    t.update(1)
                    data = {
                        'comment_body': self.__sanitize(comment.body),
                        'username': comment.author.name,
                        'permalink': comment.permalink,
                        'mhs_score' : float(),
                        'edited' : comment.edited
                    }
                    self.__data.append(data)
                    if len(self.__data) == self.__comments_n:
                        break
                    comment_tick += 1
                    #print('post :' + str(post_tick) + ' comment tick :' + str(comment_tick))
            if len(self.__data) == self.__comments_n:
                break
            post_tick += 1

    # defines a function to build comment list and author set
    def __parse_data(self):
        for data in self.__data:
            self.__sample_list.append(data['comment_body'])
            self.__author_set.add(data['username'])

    # defines a funtion to clean text in the strings from weird chars
    def __sanitize(self, item):
        item = item.strip()
        item = item.strip('\n')
        item = item.replace('\n','')
        item = item.replace('\n\n','')
        item = item.replace('\\','')
        item = item.replace('/','')
        return item
   
    # defines a funtion to perform inference on the chunks
    def __request_inferance(self, instances, apikey, url):
        payload = { "instances": instances }
        headers = {'apikey':  apikey }
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        jsonresp = response.json()
        return jsonresp

    # defines a helper function to chunk the comments for serving to inference
    def __chunker(self, iterable, chunksize):
        return zip(*[iter(iterable)] * chunksize)

    # defines a helper function to flatten the results
    def __flatten_results(self, predictions):
        for item in predictions:
            try:
                yield from self.__flatten_results(item)
            except TypeError:
                yield item

    # defines a function that carries out inference on chunks of N samples
    def __get_mhs_ratings(self, N):
        for chunk in tqdm (self.__chunker(self.__sample_list, N), total= len(self.__sample_list)/self.__chunksize, desc='Inference: '+ self.__name):
            while True:
                try:
                    response = self.__request_inferance(chunk, self.__apikey, self.__url)
                    self.__nested_results_list.append(response['predictions'])
                except requests.exceptions.HTTPError as e:
                    # could add a logging call here for the error 'e'
                    continue
                break
            pass
    
    # defines a funtion to count words
    def __count_words(self, sentence):
        return len(re.findall(r'\w+', sentence))

    # stats dictionary maps to 'Subreddit_result' ORM
    def __build_stats(self):
        arr = np.array(self.__results)
        timestamp = datetime.datetime.now()
        if len(arr) != 0:
            self.__stats = {
                'min': arr.min(),
                'max': arr.max(),
                'mean': arr.mean(),
                'std': arr.std(),
                'timestamp' : timestamp
            }
        else:
            self.__stats = {
                'min': 0.0,
                'max': 0.0,
                'mean': 0.0,
                'std': 0.0,
                'timestamp' : timestamp
            }
    
    # defines a convenience function to run inference after the object already exists or if it was created with inference=False
    def infer(self):
        """Convenience method to carry out inference on the Sub after it has been constructed with inference=False"""
        self.__get_mhs_ratings(self.__chunksize)
        self.__results = self.__flatten_results(self.__nested_results_list)
        self.__results = list(self.__results)
        self.__append_results_data()
        self.__build_stats()
    
    # defines a function to append the results list to the data member
    def __append_results_data(self):
        for (result, data) in zip(self.__results, self.__data):
            data['mhs_score'] = result
            
    # Access functions
    def data(self):
        '''Returns the main subreddit data list of dicts'''
        return self.__data

    def info(self):
        '''Returns the subreddit metadata dict'''
        return self.__info
    
    def task(self):
        '''Returns the inference task dict'''
        return self.__task
    
    def name(self):
        """Returns the display name of the subreddit"""
        return self.__name

    def samples(self):
        """Returns the list of text samples gathered"""
        return self.__sample_list

    def results(self):
        """Returns a list of inference results"""
        return self.__results
    
    def stats(self):
        """Returns a dict of descriptive stats: [min, max, mean, std, timestamp]"""
        return self.__stats
    
    def author_set(self):
        """Returns a python set of authors"""
        return self.__author_set

    def mod_set(self):
        """Returns a python set of moderators"""
        return self.__mod_set

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
        #TODO: add sanitizer function to drop gather objects with no comments
        self.__drop_empties()
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
            if len(sample.samples()) != 0:
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

    # accessor functions
    def gather_list(self):
        return self.__Gather_list
    
    def edges_list(self):
        return self.__edges_list

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