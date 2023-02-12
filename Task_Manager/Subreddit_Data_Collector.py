from dataclasses import dataclass
from tqdm import tqdm
import praw


@dataclass
class commentData:
    comment_body: str
    username: str
    permalink: str
    mhs_score: float
    edited: bool


class Subreddit_Data_Collector:
    def __init__(self, praw_object: praw.Reddit):
        self.__praw = praw_object

    def get_Comment_Data(self, display_name, scope, min_words, forest_width, per_post_n, comments_n) -> list[commentData]:
        subreddit = self.__praw.subreddit(display_name)
        posts = subreddit.top(time_filter=scope, limit=None)
        return self.__fetch_content(name=display_name,
                                    posts=posts,
                                    comments_n=comments_n,
                                    min_words=min_words,
                                    forest_width=forest_width,
                                    per_post_n=per_post_n)

    def get_mod_set(self, display_name) -> set[str]:
        """Returns the moderators for the given subreddit"""
        subreddit = self.__praw.subreddit(display_name)
        mods = set()
        for mod in subreddit.moderator():
            mods.add(mod.name)
        return mods

    def get_author_set_from_comment_data(self, comments: dict[commentData]) -> set[str]:
        """Returns the unique authors from a collection of comments"""
        auth = set()
        auth.update([x.username for x in comments])
        return auth

    def get_custom_id(self, display_name) -> str:
        return self.__praw.subreddit(display_name).id

# below here is unimplemented

    # def data(self):
    #     '''Returns the main subreddit data list of dicts'''
    #     return self.__data

    # def info(self):
    #     '''Returns the subreddit metadata dict'''
    #     return self.__info

    # def task(self):
    #     '''Returns the inference task dict'''
    #     return self.__task

    # def name(self):
    #     """Returns the display name of the subreddit"""
    #     return self.__name

    # def samples(self):
    #     """Returns the list of text samples gathered"""
    #     return self.__sample_list

    # def results(self):
    #     """Returns a list of inference results"""
    #     return self.__results

    # def stats(self):
    #     """Returns a dict of descriptive stats: [min, max, mean, std, timestamp]"""
    #     return self.__stats

    # constructor function to build moderator list

    # constructor function to build comments list

    def __fetch_content(self, name, posts, comments_n, min_words, forest_width, per_post_n):
        t = tqdm(total=comments_n, desc=f"Collection: {name}")
        result = []
        for post in posts:
            post.comments.replace_more(limit=forest_width)
            comments = post.comments.list()
            comment_tick = 0
            for comment in comments:
                if comment_tick >= per_post_n:
                    break
                if comment.author is not None and self.__count_words(comment.body) > min_words:
                    t.update(1)
                    data = commentData(comment_body=self.__sanitize(comment.body),
                                       username=comment.author.name,
                                       permalink=comment.permalink,
                                       mhs_score=None,
                                       edited=comment.edited)
                    result.append(data)
                    if len(result) == comments_n:
                        break
                    comment_tick += 1
            if len(result) == comments_n:
                break
        return result

    # defines a funtion to clean text in the strings from weird chars
    def __sanitize(self, item: str) -> str:
        item = item.replace('\\', '')
        item = item.replace('/', '')
        item = " ".join(item.split())
        return item

    # defines a funtion to count words
    def __count_words(self, sentence: str) -> int:
        return len(sentence.split())
