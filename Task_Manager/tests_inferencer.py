import json
from functools import partialmethod
from unittest.mock import Mock, patch

import requests
from django.test import TestCase
from tqdm import tqdm

from . import commentData
from .inferencer import Inferencer

from google.cloud import secretmanager

def fetch_secret(secret_id):
    '''
    This function returns a secret payload at runtime using the secure google secrets API
    '''
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/mhs-reddit/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(name=name)
    return response.payload.data.decode('UTF-8')


class Inferencer_Test(TestCase):
    def setUp(self) -> None:
        # Silence tqdm while doing tests. Stolen from https://stackoverflow.com/questions/37091673/silence-tqdms-output-while-running-tests-or-running-the-code-via-cron
        tqdm.__init__ = partialmethod(tqdm.__init__, disable=True)
        real_apikey = fetch_secret('mhs_api_key')
        real_url = fetch_secret('mhs_api_url')
        self.realInferencer = Inferencer(real_apikey, real_url)
        self.inferencer = Inferencer("test_apikey", "www.sample.com/")

    comments = [
        commentData("bumblebees are a type of insect",
                    "username1", "permalink1", None, True),
        commentData("BURN HUMAN PEOPLE IN PITS AFTER MURDERING THEM",
                    "username2", "permalink2", None, False),
        commentData("I support human rights because its the correct thing to do",
                    "username3", "permalink3", None, True),
        commentData("Hitler was correct about the holocaust",
                    "username4", "permalink4", None, True)
    ]

    def test_chunker(self):
        chunks = self.inferencer._Inferencer__chunker(
            ["comment 1", "comment 2", "comment 3"], 2)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(len(chunks[0]), 2)
        self.assertEqual(len(chunks[1]), 1)

    def test_request_inference(self):
        with patch.object(requests,
                          'post',
                          return_value=Mock(json=Mock(return_value={"predictions": [[0.1], [0.2], [0.3]]}))):

            response = self.inferencer._Inferencer__request_inference(
                ["comment 1", "comment 2", "comment 3"])
            self.assertEqual(response, {'predictions': [[0.1], [0.2], [0.3]]})

    def test_flatten(self):
        response = self.inferencer._Inferencer__flatten([[0.1, 0.2], [0.3]])
        self.assertEqual(response, [0.1, 0.2, 0.3])

    def test_infer(self):
        with patch.object(requests,
                          'post',
                          return_value=Mock(json=Mock(return_value={"predictions": [[0.1], [0.2], [0.3], [0.4]]}))):

            result = self.inferencer.infer(self.comments, 4)
            correctResult = [
                commentData("bumblebees are a type of insect",
                            "username1", "permalink1", 0.1, True),
                commentData("BURN HUMAN PEOPLE IN PITS AFTER MURDERING THEM",
                            "username2", "permalink2", 0.2, False),
                commentData("I support human rights because its the correct thing to do",
                            "username3", "permalink3", 0.3, True),
                commentData("Hitler was correct about the holocaust",
                            "username4", "permalink4", 0.4, True)
            ]
            self.assertEqual(result, correctResult)

    # This is the only test that directly connects to mhs, everthing else is local,
    # comment it out if you don't need it
    # def test_Connection(self):
    #     res = self.realInferencer._Inferencer__request_inference(
    #         ["I support human rights because its the correct thing to do"])['predictions'][0][0]
    #     self.assertAlmostEqual(-0.484849691, res)
