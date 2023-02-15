import json
import datetime
import numpy as np
from tqdm import tqdm, trange

from gather.models import (Comment_result, Inference_task, Subreddit,
                           Subreddit_mod, Subreddit_result, Mod_edge, Author_edge)

from . import Subreddit_Data_Collector, commentData
from .inferencer import Inferencer


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
        sdc = Subreddit_Data_Collector(praw_object)

        # get the comment data for all of the subs
        all_Comment_Data = {sub:  sdc.get_Comment_Data(
            display_name=sub,
            scope=task_object.time_scale,
            min_words=task_object.min_words,
            forest_width=task_object.forest_width,
            per_post_n=task_object.per_post_n,
            comments_n=task_object.comments_n)

            for sub in task_object.subreddit_set}

        # Do inference for those subs
        # inf = Inferencer(api_key, api_url)
        # for sub in all_Comment_Data:
        #     all_Comment_Data[sub] = inf.infer(
        #         all_Comment_Data[sub], chunk_size)

        all_Mods = {
            sub: sdc.get_mod_set(sub)
            for sub in task_object.subreddit_set
        }

        all_Authors = {
            sub: sdc.get_author_set_from_comment_data(all_Comment_Data[sub])

            for sub in all_Comment_Data
        }

        # push any new subreddits to the database, and get references to them
        db_Subreddit = self.__push_Subreddits(
            sdc, list(all_Comment_Data.keys()))

        db_Subbredit_results = self.__push_Subreddit_result(allComments=all_Comment_Data,
                                                            subreddits=db_Subreddit,
                                                            inference_task=task_object
                                                            )

        self.__push_Edges(task_object, db_Subbredit_results,
                          all_Mods, all_Authors)

        self.__push_Subreddit_mod(
            mod_list=all_Mods, subreddit=db_Subreddit, result=db_Subbredit_results)
        self.__push_Comment_result(
            comments=all_Comment_Data, subreddit=db_Subreddit, result=db_Subbredit_results)

    def __push_Edges(self,
                     task: Inference_task,
                     subs: dict[str, Subreddit_result],
                     mods: dict[str, set[str]],
                     authors: dict[str, set[str]]):
        '''Wraps the edges discovered in the `__discover_edge()` method.'''

        # Mods
        keys = list(mods.keys())
        num_subreddits = len(keys)
        mod_edges = []
        for i in trange(num_subreddits, desc=f"Mod Edge Discovery:"):
            for j in range(i+1, num_subreddits):
                A = mods[keys[i]]
                B = mods[keys[j]]
                weight = len(A.intersection(B))
                if weight > 0:
                    mod_edges.append(
                        Mod_edge(from_sub=subs[A], to_Sub=subs[B], inference_task=task, weight=weight))

        Mod_edge.objects.bulk_create(mod_edges)
        # Authors
        keys = list(authors.keys())
        num_subreddits = len(keys)
        author_edges = []
        for i in trange(num_subreddits, desc=f"Mod Edge Discovery:"):
            for j in range(i+1, num_subreddits):
                A = authors[keys[i]]
                B = authors[keys[j]]
                weight = len(A.intersection(B))
                if weight > 0:
                    author_edges.append(
                        Mod_edge(from_sub=subs[A], to_Sub=subs[B], inference_task=task, weight=weight))

        Author_edge.objects.bulk_create(author_edges)

    def __create_edge(self, collection: dict[str, set[str]], context, subs: dict[str, Subreddit_result]) -> dict[str, dict[str, int]]:
        '''Discovers edges between Subreddits based on Reddit authors or moderators.'''
        keys = list(collection.keys())
        num_subreddits = len(keys)
        mod_edges = []
        for i in trange(num_subreddits, desc=f"Edge Discovery: {context}"):
            for j in range(i+1, num_subreddits):
                A = collection[keys[i]]
                B = collection[keys[j]]
                edge = len(A.intersection(B))
                if edge > 0:
                    mod_edges.append(Mod_edge())

    def __push_Subreddits(self, sdc: Subreddit_Data_Collector, subs: list[str]) -> None:
        subreddits = [
            Subreddit.objects.get_or_create(
                custom_id=sdc.get_custom_id(sub), display_name=sub)
            for sub in tqdm(subs, desc="Pushing Subreddits")
        ]

        return {sub[0].display_name: sub[0] for sub in subreddits}

    def __push_Subreddit_result(self,
                                allComments: dict[str, list[commentData]],
                                subreddits: dict[str, Subreddit],
                                inference_task: Inference_task
                                ) -> dict[str, Subreddit_result]:
        '''Saves the results for a Subreddit as a `Subreddit_result` model.'''
        result = {}
        emptyList = []
        for sub in tqdm(allComments.keys(), desc="Pushing Subreddit Results"):
            # isolate the mhs results
            arr = [c.mhs_score for c in allComments[sub] if c.mhs_score != None]

            if len(arr) < 0:
                arr = np.array(arr)
                result.update({
                    sub:
                    Subreddit_result.objects.create(subreddit=subreddits[sub],
                                                    inference_task=inference_task,
                                                    min_result=arr.min(),
                                                    max_result=arr.max(),
                                                    mean_result=arr.mean(),
                                                    std_result=arr.std(),
                                                    timestamp=datetime.datetime.now(),
                                                    edges=json.dumps(emptyList))
                })

            else:
                result.update({
                    sub:
                    Subreddit_result.objects.create(subreddit=subreddits[sub],
                                                    inference_task=inference_task,
                                                    min_result=0.0,
                                                    max_result=0.0,
                                                    mean_result=0.0,
                                                    std_result=0.0,
                                                    timestamp=datetime.datetime.now(),
                                                    edges=json.dumps(emptyList))
                })

        return result

    def __push_Subreddit_mod(self, mod_list: dict[str, set[str]], subreddit: Subreddit, result: Subreddit_result):
        '''Saves the moderators for a Subreddit as `Subreddit_mod` models.'''

        for sub in tqdm(mod_list.keys(), desc="Pushing Mods"):

            mods = [Subreddit_mod(subreddit=subreddit[sub], username=mod, subreddit_result=result[sub])
                    for mod in mod_list[sub]]
            Subreddit_mod.objects.bulk_create(mods)

    def __push_Comment_result(self, comments: dict[str, list[commentData]], subreddit: Subreddit, result: Subreddit_result):
        '''Saves the comments for a Subreddit as `Comment_result` models.'''

        for sub in tqdm(comments.keys(), desc="Pushing Comments"):
            db_comments = [Comment_result(subreddit_result=result[sub],
                                          subreddit=subreddit[sub],
                                          permalink=comment.permalink,
                                          mhs_score=(
                                              comment.mhs_score if comment.mhs_score != None else 0.0),
                                          comment_body=comment.comment_body,
                                          username=comment.username)
                           for comment in comments[sub]]
            Comment_result.objects.bulk_create(db_comments)
