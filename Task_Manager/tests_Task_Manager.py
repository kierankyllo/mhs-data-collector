import datetime
import json
import random
from functools import partialmethod
from unittest.mock import MagicMock, patch

import praw
import pytz
from django.test import TestCase
from tqdm import tqdm

from gather.models import (Author_edge, Comment_result, Inference_task,
                           Mod_edge, Subreddit, Subreddit_mod,
                           Subreddit_result)
from Task_Manager import Task_Manager
from Task_Manager.Subreddit_Data_Collector import commentData

from google.cloud import secretmanager

def fetch_secret(secret_id):
    '''
    This function returns a secret payload at runtime using the secure google secrets API 
    '''
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/mhs-reddit/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode('UTF-8')


class TestTaskManager(TestCase):
    def setUp(self) -> None:
        # Silence tqdm while doing tests. Stolen from https://stackoverflow.com/questions/37091673/silence-tqdms-output-while-running-tests-or-running-the-code-via-cron
        tqdm.__init__ = partialmethod(tqdm.__init__, disable=True)
        self.task_manager = Task_Manager()
        self.now = datetime.datetime.now

        self.praw_obj = praw.Reddit(
            client_id=fetch_secret('praw_client_id'),
            client_secret=fetch_secret('praw_client_secret'),
            password=fetch_secret('praw_client_password'),
            user_agent=fetch_secret('praw_user_agent'),
            username=fetch_secret('praw_user_name')
        )

    @patch.object(Task_Manager, '_instance', None)
    def test_singleton(self):
        """Test that the Task_Manager is a singleton"""
        task_manager1 = Task_Manager()
        task_manager2 = Task_Manager()
        self.assertIs(task_manager1, task_manager2)

    def test_push_Edges(self):
        # Prepare data
        subreddit1 = Subreddit.objects.create(custom_id=1,
                                              display_name='test_subreddit1')
        subreddit2 = Subreddit.objects.create(custom_id=2,
                                              display_name='test_subreddit2')
        task = Inference_task.objects.create(start_sched=self.now(),
                                             time_scale='week',
                                             min_words=10,
                                             forest_width=10,
                                             per_post_n=5,
                                             comments_n=100,
                                             status=0,
                                             subreddit_set=[
                                                 subreddit1.display_name, subreddit2.display_name],
                                             )
        subreddit_result1 = Subreddit_result.objects.create(subreddit=subreddit1,
                                                            inference_task=task,
                                                            edges={})
        subreddit_result2 = Subreddit_result.objects.create(subreddit=subreddit2,
                                                            inference_task=task,
                                                            edges={})

        mods = {'test_subreddit1': set(['mod1', 'mod2']),
                'test_subreddit2': set(['mod2', 'mod3'])}
        authors = {'test_subreddit1': set(['author1', 'author2']),
                   'test_subreddit2': set(['author2', 'author3'])}

        # Execute method
        self.task_manager._Task_Manager__push_Edges(task, {
            'test_subreddit1': subreddit_result1,
            'test_subreddit2': subreddit_result2
        }, mods, authors)

        # Check that the edges were created
        self.assertEqual(Mod_edge.objects.count(), 1)
        self.assertEqual(Author_edge.objects.count(), 1)

    def test_push_subreddit_result_with_inference(self):
        subDict = {"subreddit10": Subreddit.objects.create(custom_id='abc', display_name='test_subreddit10'),
                   "subreddit20":  Subreddit.objects.create(custom_id="def", display_name='test_subreddit20'), }
        task = Inference_task.objects.create(start_sched=self.now(),
                                             time_scale='week',
                                             min_words=10,
                                             forest_width=10,
                                             per_post_n=5,
                                             comments_n=100,
                                             status=0,
                                             subreddit_set=[
                                                 "test_subreddit10", "test_subreddit20"],
                                             )

        # create a list of fake data
        comments = []
        for i in range(20):
            comment = commentData(
                comment_body=f"Comment {i+1}",
                username=f"User {i+1}",
                permalink=f"https://example.com/comment/{i+1}",
                mhs_score=random.uniform(1, 5),
                edited=random.choice([True, False])
            )
            comments.append(comment)

        # Split the list into two
        allcomments = {
            "subreddit10": comments[:10], "subreddit20": comments[10:]}
        # run the service
        self.task_manager._Task_Manager__push_Subreddit_result(
            allcomments, subDict, task)
        saved_results = Subreddit_result.objects.all().order_by('subreddit__display_name')
        self.assertEqual(len(saved_results), 2)
        self.assertEqual(saved_results[0].subreddit, subDict['subreddit10'])
        self.assertGreater(saved_results[0].mean_result, 0)
        self.assertEqual(saved_results[0].inference_task, task)
        self.assertEqual(saved_results[1].subreddit, subDict['subreddit20'])
        self.assertGreater(saved_results[0].mean_result, 0)
        self.assertEqual(saved_results[1].inference_task, task)

    # def test_fullRun(self) -> None:
    #     sublist = ['programming', 'rpcs3', 'subnautica', 'formula1']

    #     task_out = Inference_task.objects.create(start_sched=self.now(),
    #                                              time_scale='week',
    #                                              min_words=1,
    #                                              forest_width=1,
    #                                              per_post_n=100,
    #                                              comments_n=10,
    #                                              subreddit_set=sublist,
    #                                              status='0',
    #                                              )
    #     tm = Task_Manager()

    #     tm.do_Task(task_out, fetch_secret('mhs_api_url'),
    #                fetch_secret('mhs_api_key'), self.praw_obj)
