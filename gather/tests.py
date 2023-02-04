from django.test import TestCase
from gather.models import Subreddit, Subreddit_mod, Subreddit_result
from django.db.utils import IntegrityError
from django.db.transaction import TransactionManagementError

# MODEL TESTS
# TODO: Inference_task
# TODO: Subreddit_result
# TODO: Subreddit_mod
# TODO: Comment_result


class Subreddit_Test(TestCase):
    def setUp(self):
        Subreddit.objects.create(
            custom_id="1a2b3c", display_name="ThisIsASub")

    def insert_Duplicate(self):
        Subreddit.objects.create(
            custom_id="1a2b3cd", display_name="ThisIsASub")
        Subreddit.objects.create(
            custom_id="1a2b3cd", display_name="ThisIsASecondSub")

    def insert_Long_Custom_ID(self):
        Subreddit.objects.create(
            custom_id="1a2b3s4d5f6g7h8u9i0o1p", display_name="ThisSubIDIsToLong")

    def insert_Long_Display_Name(self):
        Subreddit.objects.create(
            custom_id="1a2s3d3f", display_name="ThisDisplayNameIsWayToLongForTheDatabase")

    def test_Subreddit(self):
        correct = Subreddit.objects.get(custom_id="1a2b3c")
        self.assertEqual(correct.display_name, "ThisIsASub")
        self.assertEqual(correct.__str__(), "ThisIsASub")
        self.assertRaises(IntegrityError, self.insert_Duplicate)
        self.assertRaises(TransactionManagementError,
                          self.insert_Long_Custom_ID)
        self.assertRaises(TransactionManagementError,
                          self.insert_Long_Display_Name)
