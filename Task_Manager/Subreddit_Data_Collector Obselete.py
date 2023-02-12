import datetime
import json
import re
from dataclasses import dataclass
import numpy as np
import requests
from tqdm import tqdm

# sys.path.append('/home/kyllo/projects/gather_bot/gather')
# os.environ['DJANGO_SETTINGS_MODULE'] = 'mysite.settings'
# django.setup()


# TODO: build test scripts for the class
# TODO: debug using 'issues' workflow
# TODO: add error handling code
# TODO: docstrings and code formatting compliance
# TODO: Seperate Inferencing into its own class
# TODO: Make the data collector return a data object

@dataclass
class commentData:
    comment_body: str
    username: str
    permalink: str
    mhs_score: float
    edited: bool


class Subreddit_Data_Collector:
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
            'custom_id': self.__sub.id,
            'display_name': display_name,
        }
        # task dictionary maps to 'Inference_Task' ORM
        self.__task = {
            'time_scale': scope,
            'min_words': min_words,
            'forest_width': forest_width,
            'per_post_n': per_post_n,
            'comments_n': comments_n,
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
        t = tqdm(total=self.__comments_n, desc='Collection: ' + self.__name)
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
                    data = commentData(comment_body=self.__sanitize(comment.body),
                                       username=comment.author.name,
                                       permalink=comment.permalink,
                                       edited=comment.edited)
                    self.__data.append(data)
                    if len(self.__data) == self.__comments_n:
                        break
                    comment_tick += 1
                    # print('post :' + str(post_tick) + ' comment tick :' + str(comment_tick))
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
        item = item.replace('\n', '')
        item = item.replace('\n\n', '')
        item = item.replace('\\', '')
        item = item.replace('/', '')
        return item

    # defines a funtion to perform inference on the chunks
    def __request_inferance(self, instances, apikey, url):
        payload = {"instances": instances}
        headers = {'apikey':  apikey}
        response = requests.post(
            url, data=json.dumps(payload), headers=headers)
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
        for chunk in tqdm(self.__chunker(self.__sample_list, N), total=len(self.__sample_list)/self.__chunksize, desc='Inference: ' + self.__name):
            while True:
                try:
                    response = self.__request_inferance(
                        chunk, self.__apikey, self.__url)
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
                'timestamp': timestamp
            }
        else:
            self.__stats = {
                'min': 0.0,
                'max': 0.0,
                'mean': 0.0,
                'std': 0.0,
                'timestamp': timestamp
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
