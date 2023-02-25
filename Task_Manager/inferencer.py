from tqdm import tqdm
import requests
import logging
from . import commentData


class Inferencer():
    """
    Class for running inference on comments.

    This class is used to perform sentiment analysis on a list of comments by sending
    chunks of comments to an API for inference. The result of the inference is then
    combined with the original comments to produce a list of comment objects, each
    with a `mhs_score` attribute representing the sentiment score of the comment.

    Args:
        apikey (str): API Key to be used for sending requests to the inference API.
        url (str): URL of the inference API.

    Methods:
        infer: Runs inference on the list of comments.

    """

    def __init__(self, apikey: str, url: str) -> None:
        """
        Initializes the Inferencer class with the API Key and URL.

        Args:
            apikey (str): API Key for accessing the inference service.
            url (str): URL for the inference service.

        """
        self.__apikey = apikey
        self.__url = url

    def infer(self, comments: list[commentData], chunk_size: int) -> list[commentData]:
        """
        Performs sentiment analysis on the comments.

        Args:
            comments (list[commentData]): List of comment data objects.
            chunk_size (int): The size of chunks to make the inference.

        Returns:
            list[commentData]: List of comment data objects with the `mhs_score` field filled.

        """
        response = []
        comment_text = [x.comment_body for x in comments]
        for chunk in tqdm(self.__chunker(comment_text, chunk_size), desc=f"Inference:"):
            data = self.__request_inference(chunk)
            if (data == None):
                logging.error("UNABLE TO PERFORM INFERENCE")
                continue
            response.extend(data['predictions'])

        response = self.__flatten(response)
        return self.__combineResults(comments, response)

    def __chunker(self, data: list[str], chunk_size: int) -> list[str]:
        """
        Chunks the data into the specified chunk size.
        """
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    def __request_inference(self, data):
        payload = {"instances": data}
        headers = {"apikey": self.__apikey}
        for attempts in range(5):
            try:
                response = requests.post(
                    self.__url, json=payload, headers=headers)
                return response.json()
            except requests.exceptions.HTTPError as e:
                logging.warning(f"{e}\nTrying {5-attempts} more times")
                continue
        return None

    def __flatten(self, data):
        return [item for sublist in data for item in sublist]

    def __combineResults(self, comments: list[commentData], scores: list[float]) -> list[commentData]:
        for score, comment in zip(scores, comments):
            comment.mhs_score = score
        return comments
