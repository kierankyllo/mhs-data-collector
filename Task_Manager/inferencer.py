from tqdm import tqdm
import requests
from . import commentData


class Inferencer():
    def __init__(self, apikey: str, url: str) -> None:
        self.__apikey = apikey
        self.__url = url

    def infer(self, comments: list[commentData], chunk_size: int) -> list[commentData]:
        response = []

        t = tqdm(total=len(comments), desc=f"Inference")
        comment_text = [x.comment_body for x in comments]
        for chunk in self.__chunker(comment_text, chunk_size):
            for attempts in range(5):
                try:
                    res = self.__request_inference(chunk)
                    response.extend(res['predictions'])
                except requests.exceptions.HTTPError as e:
                    print(f"{e}\nTrying {5-attempts} more times")
                    continue
                t.update(len(chunk))
                break

        response = self.__flatten(response)
        return self.__combineResults(comments, response)

    def __chunker(self, data: list[str], chunk_size: int) -> list[str]:
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    def __request_inference(self, data):
        payload = {"instances": data}
        headers = {"apikey": self.__apikey}
        response = requests.post(
            self.__url, json=payload, headers=headers)
        return response.json()

    def __flatten(self, data):
        return [item for sublist in data for item in sublist]

    def __combineResults(self, comments: list[commentData], scores: list[float]) -> list[commentData]:
        for score, comment in zip(scores, comments):
            comment.mhs_score = score
        return comments
