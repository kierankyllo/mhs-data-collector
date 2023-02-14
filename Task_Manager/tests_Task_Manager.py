from unittest.mock import MagicMock, patch

from django.test import TestCase
from tqdm import tqdm
import datetime
import json
import praw

from gather.models import (Comment_result, Inference_task, Subreddit,
                           Subreddit_mod, Subreddit_result)
from Task_Manager import Task_Manager
from Task_Manager.Subreddit_Data_Collector import Subreddit_Data_Collector


class TestTaskManager(TestCase):
    def setUp(self) -> None:
        self.tm = Task_Manager()

        keysJSON = open('keys.json')
        open_file = keysJSON.read()
        self.model_attribs = json.loads(open_file)['model']
        keys = json.loads(open_file)['reddit']
        keysJSON.close()

        self.praw_obj = praw.Reddit(
            client_id=keys['client_id'],
            client_secret=keys['client_secret'],
            password=keys['password'],
            user_agent="web:mhs-crawler-bot:v1 (by /u/mhs-crawler-bot)",
            username="mhs-crawler-bot",
        )

    def test_fullRun(self) -> None:
        now = datetime.datetime.now()
        sublist = ['programming', 'rpcs3', 'subnautica', 'formula1']

        task_out = Inference_task.objects.create(start_sched=now,
                                                 time_scale='week',
                                                 min_words=1,
                                                 forest_width=1,
                                                 per_post_n=100,
                                                 comments_n=10,
                                                 subreddit_set=sublist,
                                                 status='0',
                                                 )
        tm = Task_Manager()

        tm.do_Task(task_out, "https://kyllobrooks.com/api/mhs",
                   self.model_attribs['apikey'], self.praw_obj)
