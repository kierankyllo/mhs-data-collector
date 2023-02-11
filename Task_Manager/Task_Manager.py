import json

from tqdm import tqdm

from gather.models import (Comment_result, Inference_task, Subreddit,
                           Subreddit_mod, Subreddit_result)

from . import Subreddit_Data_Collector

# TODO: build test scripts for the class
# TODO: debug using 'issues' workflow
# TODO: add terminal feedback about edge building and database pushing progress using tqdm
# TODO: add error handling code
# TODO: docstrings and code formatting compliance


class Task_Manager():
    '''
    The `Task_Manager` class is a singleton responsible for processing a `task_object` and aggregating information
    related to the task such as Subreddits, Reddit authors, and Reddit moderators.
    The class uses the `Get_Subreddit` class to obtain information from the Reddit API.
    The information collected is stored on the database.

    Parameters:

    - `task_object`: An object representing a task.
    - `api_url`: The URL for the MHS API.
    - `api_key`: An API key for accessing the MHS API.
    - `praw_object`: An object for accessing the Reddit API using the `praw` library.
    - `chunk_size` (optional, default=100): The size of the chunks used to process information from the Reddit API.
    '''

    # this will be set the first time that it is created
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Task_Manager, cls).__new__(cls)
            # any intialization goes below here
        return cls._instance

    def do_Task(self, task_object: Inference_task, api_url, api_key, praw_object, chunk_size=100) -> None:

        Gather_list = self.__build_Gather_lists(
            task_object, api_url, api_key, praw_object, chunk_size)
        edges_lists = self.__wrap_edges(Gather_list)
        self.__push_All(Gather_list, edges_lists, task_object)

    def __build_Gather_lists(self, task_object: Inference_task, api_url, api_key, praw_object, chunk_size):
        '''
        Builds a list of `Get_Subreddit` objects.
        '''
        Gather_list = [Subreddit_Data_Collector(sub,
                                                api_url,
                                                api_key,
                                                praw_object,
                                                scope=task_object.time_scale,
                                                min_words=task_object.min_words,
                                                inference=True,
                                                forest_width=task_object.forest_width,
                                                per_post_n=task_object.per_post_n,
                                                comments_n=task_object.comments_n,
                                                chunk_size=chunk_size
                                                )
                       for sub in task_object.subreddit_set]
        # remove any subreddits that don't have the rquested number of comments
        filter(lambda s: len(s.samples()) == task_object.comments_n)
        return Gather_list

    def __wrap_edges(self, Gather_list: Subreddit_Data_Collector):
        '''Wraps the edges discovered in the `__discover_edge()` method.'''
        mods_edges = self.__discover_edge('mods', Gather_list)
        authors_edges = self.__discover_edge('authors', Gather_list)
        wrapper = []
        for (m, a) in zip(mods_edges, authors_edges):
            data = {"mods": m, "authors": a}
            wrapper.append(data)
        return wrapper

    def __discover_edge(self, context, Gather_list: Subreddit_Data_Collector):
        '''Discovers edges between Subreddits based on Reddit authors or moderators.'''
        num_subreddits = len(Gather_list)
        t = tqdm(total=num_subreddits, desc='Edge Discovery : ' + context)
        outer = []
        for i in range(num_subreddits):
            inner = {}
            t.update(1)
            for j in range(i+1, num_subreddits):
                A, B
                if context == 'mods':
                    A = Gather_list[i].mod_set()
                    B = Gather_list[j].mod_set()

                if context == 'authors':
                    A = Gather_list[i].author_set()
                    B = Gather_list[j].author_set()

                edge = len(A.intersection(B))
                if edge > 0:
                    data = {Gather_list[j].name(): edge}
                    inner.update(data)
            outer.append(inner)
        return outer

    def __push_All(self, Gather_list: Subreddit_Data_Collector, edges_list, task: Inference_task):
        '''Calls methods to save the information for each Subreddit.'''
        t = tqdm(total=len(Gather_list), desc='Database Push : ')
        assert (len(Gather_list) == len(edges_list)), 'list size mismatch'
        for (gather, edge) in zip(Gather_list, edges_list):
            self.__push_SubredditData(gather, edge, task)
            t.update(1)

    def __push_SubredditData(self, sub_object: Subreddit_Data_Collector, edges, task):
        s = self.__push_Subreddit(sub_object)
        r = self.__push_Subreddit_result(sub_object, edges, s, task)
        self.__push_Subreddit_mod(sub_object, s, r)
        self.__push_Comment_result(sub_object, s, r)

    def __push_Subreddit(self, sub_object: Subreddit_Data_Collector):
        custom_id = sub_object.info()["custom_id"]
        display_name = sub_object.info()["display_name"]
        sub, created = Subreddit.objects.get_or_create(
            custom_id=custom_id, display_name=display_name)
        return sub

    def __push_Subreddit_result(self, sub_object: Subreddit_Data_Collector, edges, subreddit, inference_task):
        '''Saves the results for a Subreddit as a `Subreddit_result` model.'''
        min = sub_object.stats()['min']
        max = sub_object.stats()['max']
        mean = sub_object.stats()['mean']
        std = sub_object.stats()['std']
        timestamp = sub_object.stats()['timestamp']
        return Subreddit_result.objects.create(subreddit=subreddit,
                                               inference_task=inference_task,
                                               min_result=min,
                                               max_result=max,
                                               mean_result=mean,
                                               std_result=std,
                                               timestamp=timestamp,
                                               edges=json.dumps(edges))

    def __push_Subreddit_mod(self, sub_object: Subreddit_Data_Collector, subreddit, result):
        '''Saves the moderators for a Subreddit as `Subreddit_mod` models.'''
        mods = [Subreddit_mod(subreddit=subreddit, username=mod, subreddit_result=result)
                for mod in sub_object.mod_set()]
        Subreddit_mod.objects.bulk_create(mods)

    def __push_Comment_result(self, sub_object: Subreddit_Data_Collector, subreddit, result):
        '''Saves the comments for a Subreddit as `Comment_result` models.'''
        comments = [Comment_result(subreddit_result=result,
                                   subreddit=subreddit,
                                   permalink=x['permalink'],
                                   mhs_score=x['mhs_score'],
                                   comment_body=x['comment_body'],
                                   username=x['username'])
                    for x in sub_object.data()]
        Comment_result.objects.bulk_create(comments)
