from django.test import TestCase
from gather.models import Subreddit

# MODEL TESTS (Theoretically these shouldn't run on the production database according to the django docs)
# TODO: Subreddit
# TODO: Inference_task
# TODO: Subreddit_result
# TODO: Subreddit_mod
# TODO: Comment_result


class Subreddit_Test(TestCase):
    def setUp(self):
        Subreddit.objects.create(
            custom_id="1a2b3c", display_name="ThisIsASub")
        # Subreddit.objects.create(
        #     custom_id="1a2b3c", display_name="DuplicateName")
        # Subreddit.objects.create(
        #     custom_id="1a2b3s4d5f6g7h8u9i0o1p", display_name="ThisSubIDIsToLong")
        # Subreddit.objects.create(
        #     custom_id="1a2s3d3f", display_name="ThisDisplayNameIsWayToLongForTheDatabase")

    def test_Subreddit(self):
        correct = Subreddit.objects.get(custom_id="1a2b3c")
        # to_Long_ID = Subreddit.objects.get(custom_id="1a2b3s4d5f6g7h8u9i0o1p")
        # to_Long_Display_Name = Subreddit.objects.get(custom_id="1a2s3d3f")

        self.assertEqual(correct.display_name, "ThisIsASub")
        # self.assertEqual(hasattr(to_Long_ID.display_name), False)
        # self.assertEqual(hasattr(to_Long_Display_Name.display_name), False)
