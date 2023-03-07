from functools import partialmethod
from unittest.mock import Mock, patch

import requests
from django.test import TestCase
from tqdm import tqdm
import praw

from .Subreddit_Data_Collector import Subreddit_Data_Collector
from google.cloud import secretmanager


def fetch_secret(secret_id):
    '''
    This utility function returns a secret payload at runtime using the secure google secrets API 
    '''
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/mhs-reddit/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode('UTF-8')


class Inferencer_Test(TestCase):
    def setUp(self) -> None:
        # Silence tqdm while doing tests. Stolen from https://stackoverflow.com/questions/37091673/silence-tqdms-output-while-running-tests-or-running-the-code-via-cron
        tqdm.__init__ = partialmethod(tqdm.__init__, disable=True)

        self.praw_obj = praw.Reddit(
            client_id=fetch_secret('praw_client_id'),
            client_secret=fetch_secret('praw_client_secret'),
            password=fetch_secret('praw_client_password'),
            user_agent=fetch_secret('praw_user_agent'),
            username=fetch_secret('praw_user_name')
        )

        self.sdc = Subreddit_Data_Collector(self.praw_obj)

    def Test_AutoMod_Filter(self):
        # get a subreddit that uses automod, might need to be changed if it starts to fail
        display_name = 'discordapp'

        subMods = self.praw_obj.subreddit(display_name).moderators()

        self.assertEqual(len(subMods) - 1,
                         len(self.sdc.get_mod_set(display_name, False)))
        self.assertEqual(len(subMods),
                         len(self.sdc.get_mod_set(display_name, True)))
