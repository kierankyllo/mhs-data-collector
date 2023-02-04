from gather.models import Subreddit, Subreddit_result, Subreddit_mod, Comment_result
from tqdm import tqdm
import Gather
import json
import sys
import os
import django

sys.path.append('/home/kyllo/projects/gather_bot/gather')
os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'
django.setup()

# TODO: build test scripts for the class
# TODO: debug using 'issues' workflow
# TODO: add terminal feedback about edge building and database pushing progress using tqdm
# TODO: add error handling code
# TODO: docstrings and code formatting compliance


class Task_Manager():
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
            # only append gather objects containing samples
            # could also be used to drop gather objects with samples less than comments_n if we want
            if len(sample.samples()) != 0:
                self.__Gather_list.append(sample)
                self.__subreddit_list.append(sample.name)

    # this sucked to write i need a whiteboard to explain it
    def __discover_JSON_edges(self, context):
        t = tqdm(total=self.__dims, desc='Edge Discovery : ' + context)
        outer = []
        for i in range(self.__dims):
            inner = {}
            t.update(1)
            for j in range(i+1, self.__dims):

                if context == 'mods':
                    A = self.__Gather_list[i].mod_set()
                    B = self.__Gather_list[j].mod_set()
                    intersect = A.intersection(B)
                    cardinality = len(intersect)
                    if cardinality > 0:
                        data = {self.__Gather_list[j].name(): cardinality}
                        inner.update(data)

                if context == 'authors':
                    A = self.__Gather_list[i].author_set()
                    B = self.__Gather_list[j].author_set()
                    intersect = A.intersection(B)
                    cardinality = len(intersect)
                    if cardinality > 0:
                        data = {self.__Gather_list[j].name(): cardinality}
                        inner.update(data)

            outer.append(inner)
        return outer

    def __wrap_JSON_edges(self):

        mods_edges = self.__discover_JSON_edges('mods')
        authors_edges = self.__discover_JSON_edges('authors')
        wrapper = []
        for (m, a) in zip(mods_edges, authors_edges):
            data = {"mods": m, "authors": a}
            wrapper.append(data)
        return wrapper

    def __push_Subreddit(self, sub_object):
        custom_id = sub_object.info()['pk']
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
        r = Subreddit_result(subreddit=subreddit,
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
            r = Subreddit_mod(subreddit=subreddit,
                              username=mod, subreddit_result=result)
            r.save()

    def __push_Comment_result(self, sub_object, subreddit, result):
        for comment in sub_object.data():
            subreddit_result = result
            subreddit = subreddit
            permalink = comment['permalink']
            mhs_score = comment['mhs_score']
            comment_body = comment['comment_body']
            username = comment['username']
            r = Comment_result(subreddit_result=result,
                               subreddit=subreddit,
                               permalink=permalink,
                               mhs_score=mhs_score,
                               comment_body=comment_body,
                               username=username)
            r.save()

    def __push_Gather(self, sub_object, edges, task):
        s = self.__push_Subreddit(sub_object)
        r = self.__push_Subreddit_result(sub_object, edges, s, task)
        self.__push_Subreddit_mod(sub_object, s, r)
        self.__push_Comment_result(sub_object, s, r)

    def __push_All(self):
        t = tqdm(total=len(self.__Gather_list), desc='Database Push : ')
        assert (len(self.__Gather_list) == len(
            self.__edges_list)), 'list size mismatch'
        for (gather, edge) in zip(self.__Gather_list, self.__edges_list):
            self.__push_Gather(gather, edge, self.__task)
            t.update(1)

    # accessor functions
    def gather_list(self):
        return self.__Gather_list

    def edges_list(self):
        return self.__edges_list
