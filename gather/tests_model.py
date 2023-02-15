from django.test import TestCase
from django.utils import timezone
from .models import Subreddit, Inference_task, Subreddit_mod, Subreddit_result, Comment_result
from django.db.utils import IntegrityError
from django.db.transaction import TransactionManagementError

# MODEL TESTS
# TODO: add tests for Mod_edge, Author_edge


class Subreddit_Test(TestCase):
    def insert_Correct_Data(self):
        Subreddit.objects.create(
            custom_id="1a2b3c", display_name="ThisIsASub")
        correct = Subreddit.objects.get(custom_id="1a2b3c")
        self.assertEqual(correct.display_name, "ThisIsASub")
        self.assertEqual(correct.__str__(), "ThisIsASub")

    def insert_Duplicate(self):
        def insert_dup():
            Subreddit.objects.create(
                custom_id="1a2b3cd", display_name="ThisIsASub")
            Subreddit.objects.create(
                custom_id="1a2b3cd", display_name="ThisIsASecondSub")
        self.assertRaises(IntegrityError, insert_dup)

    def insert_Long_Custom_ID(self):
        def insert_long_id():
            Subreddit.objects.create(
                custom_id="1a2b3s4d5f6g7h8u9i0o1p", display_name="ThisSubIDIsToLong")
        self.assertRaises(TransactionManagementError, insert_long_id)

    def insert_Long_Display_Name(self):
        def insert_long_name():
            Subreddit.objects.create(
                custom_id="1a2s3d3f", display_name="ThisDisplayNameIsWayToLongForTheDatabase")
        self.assertRaises(TransactionManagementError, insert_long_name)

    def test_Subreddit(self):
        self.insert_Correct_Data()
        self.insert_Duplicate()
        self.insert_Long_Custom_ID()
        self.insert_Long_Display_Name()


class Inference_Task_Test(TestCase):
    def setUp(self):
        self.now = timezone.now()
        Inference_task.objects.create(
            start_sched=self.now,
            time_scale="hour",
            min_words=20,
            forest_width=10,
            per_post_n=1000,
            comments_n=1000,
            subreddit_set=["django", "python"],
            status=0
        )

    def test_inference_task_creation(self):
        task = Inference_task.objects.get(start_sched=self.now)
        self.assertEqual(task.time_scale, "hour")
        self.assertEqual(task.min_words, 20)
        self.assertEqual(task.forest_width, 10)
        self.assertEqual(task.per_post_n, 1000)
        self.assertEqual(task.comments_n, 1000)
        self.assertEqual(task.subreddit_set, ["django", "python"])
        self.assertEqual(task.status, 0)


class Subreddit_Result_Test(TestCase):
    def setUp(self):
        # Create Subreddit and Inference_task objects to be used in tests
        self.subreddit = Subreddit.objects.create(
            custom_id="1a2b3cd", display_name="test_subreddit")
        self.inference_task = Inference_task.objects.create(
            start_sched=timezone.now(),
            time_scale="hour",
            min_words=20,
            forest_width=10,
            per_post_n=1000,
            comments_n=1000,
            subreddit_set=["django", "python"],
            status=0
        )
        self.subreddit_result = Subreddit_result.objects.create(
            subreddit=self.subreddit,
            inference_task=self.inference_task,
            min_result=1.0,
            max_result=10.0,
            mean_result=5.0,
            std_result=2.0,
            edges=[{"node1": "a", "node2": "b"}]
        )

    def test_subreddit_result_created(self):
        """Test if a Subreddit_result object is created successfully"""
        self.assertEqual(Subreddit_result.objects.count(), 1)

    def test_subreddit_result_str(self):
        """Test if the __str__ method returns the expected output"""
        self.assertEqual(str(self.subreddit_result),
                         "Results for test_subreddit collected on " + str(self.inference_task.start_sched))

    def test_subreddit_result_data(self):
        """Test if the Subreddit_result object contains the expected data"""
        self.assertEqual(self.subreddit_result.subreddit, self.subreddit)
        self.assertEqual(self.subreddit_result.inference_task,
                         self.inference_task)
        self.assertEqual(self.subreddit_result.min_result, 1.0)
        self.assertEqual(self.subreddit_result.max_result, 10.0)
        self.assertEqual(self.subreddit_result.mean_result, 5.0)
        self.assertEqual(self.subreddit_result.std_result, 2.0)
        self.assertEqual(self.subreddit_result.edges, [
                         {"node1": "a", "node2": "b"}])


class Subreddit_Mod_Test(TestCase):
    def setUp(self):
        inference_task = Inference_task.objects.create(
            start_sched=timezone.now(),
            time_scale="hour",
            min_words=20,
            forest_width=10,
            per_post_n=1000,
            comments_n=1000,
            subreddit_set=["django", "python"],
            status=0
        )
        subreddit = Subreddit.objects.create(
            custom_id="1a2b3cd", display_name="test_subreddit"
        )
        subreddit_result = Subreddit_result.objects.create(
            subreddit=subreddit,
            inference_task=inference_task,
            min_result=1.0,
            max_result=2.0,
            mean_result=1.5,
            std_result=0.5,
            edges={}
        )
        Subreddit_mod.objects.create(
            subreddit=subreddit,
            subreddit_result=subreddit_result,
            username="test_user"
        )

    def test_str_representation(self):
        mod = Subreddit_mod.objects.get(username="test_user")
        self.assertEqual(
            str(mod), "User: test_user, Subreddit: test_subreddit")

    def test_foreign_key_relationships(self):
        mod = Subreddit_mod.objects.get(username="test_user")
        self.assertEqual(mod.subreddit.display_name, "test_subreddit")
        self.assertEqual(
            mod.subreddit_result.subreddit.display_name, "test_subreddit")


class CommentResultModelTestCase(TestCase):
    def setUp(self):
        self.subreddit = Subreddit.objects.create(
            custom_id='test_subreddit', display_name='Test Subreddit')
        self.inference_task = Inference_task.objects.create(
            start_sched=timezone.now(),
            time_scale="hour",
            min_words=20,
            forest_width=10,
            per_post_n=1000,
            comments_n=1000,
            subreddit_set=["django", "python"],
            status=0
        )
        self.subreddit_result = Subreddit_result.objects.create(
            subreddit=self.subreddit,
            inference_task=self.inference_task,
            min_result=1.0,
            max_result=10.0,
            mean_result=5.0,
            std_result=2.0,
            edges=[{"node1": "a", "node2": "b"}]
        )

    def test_comment_result_str(self):
        comment_result = Comment_result.objects.create(
            subreddit_result=self.subreddit_result,
            subreddit=self.subreddit,
            permalink='https://www.example.com/test_comment',
            mhs_score=0.5,
            comment_body='This is a test comment',
            username='testuser'
        )
        self.assertEqual(str(
            comment_result), "Post By: testuser in: Test Subreddit.\nScore: 0.5.\nText: This is a test comment")

    def test_comment_result_foreign_key(self):
        comment_result = Comment_result.objects.create(
            subreddit_result=self.subreddit_result,
            subreddit=self.subreddit,
            permalink='https://www.example.com/test_comment',
            mhs_score=0.5,
            comment_body='This is a test comment',
            username='testuser')
        self.assertEqual(comment_result.subreddit_result,
                         self.subreddit_result)
        self.assertEqual(comment_result.subreddit, self.subreddit)
