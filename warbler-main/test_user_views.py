"""User View Tests"""

from http.client import ResponseNotReady
from app import app, CURR_USER_KEY
import os
from unittest import TestCase

from models import db, connect_db, Message, User, Likes, Follows
from bs4 import BeautifulSoup

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


db.create_all()

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for Messages"""

    def setUp(self):
        """Create test client and add sample data"""

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@email.com",
                                    password="password",
                                    image_url=None)
        self.testuser_id = 1111
        self.testuser.id = self.testuser_id

        self.user1 = User.signup("user1", "user1@email.com", "password", None)
        self.user1_id = 2222
        self.user1.id = self.user1_id
        self.user2 = User.signup("user2", "user2@email.com", "password", None)
        self.user2_id = 3333
        self.user2.id = self.user2_id
        self.user3 = User.signup("user3", "user3@email.com", "password", None)
        self.user4 = User.signup("user4", "user4@email.com", "password", None)

        db.session.commit()

    def tearDown(self):
        resp = super().tearDown()
        db.session.rollback()
        return resp

    def test_users_index(self):
        with self.client as c:
            resp = c.get("/users")

            self.assertIn("@testuser", str(resp.data))
            self.assertIn("@user1", str(resp.data))
            self.assertIn("@user2", str(resp.data))
            self.assertIn("@user3", str(resp.data))
            self.assertIn("@user4", str(resp.data))

    def test_users_search(self):
        with self.client as c:
            resp = c.get("/users?q=testuser")

            self.assertIn("@testuser", str(resp.data))
            self.assertNotIn("@user1", str(resp.data))
            self.assertNotIn("@user2", str(resp.data))
            self.assertNotIn("@user3", str(resp.data))
            self.assertNotIn("@user4", str(resp.data))

    def test_user_show(self):
        with self.client as c:
            resp = c.get(f"/users/{self.testuser_id}")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("@testuser", str(resp.data))

    def setup_likes(self):
        m1 = Message(text="test message 1", user_id=self.testuser_id)
        m2 = Message(text="test message 2", user_id=self.testuser_id)
        m3 = Message(id=343434, text="test message 3", user_id=self.user1_id)
        db.session.add([m1, m2, m3])
        db.session.commit()

        l1 = Likes(user_id=self.testuser_id, message_id=343434)

        db.session.add(l1)
        db.session.commit()

    def test_user_show_with_likes(self):
        self.setup_likes()

        with self.client as c:
            resp = c.get(f"/users/{self.testuser_id}")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("@testuser", str(resp.data))
            soup = BeautifulSoup(str(resp.data), 'html.parser')
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)
            # test for a count of 2 messages
            self.assertIn("2", found[0].text)
            # test for a count of 0 followers
            self.assertIn("0", found[1].text)
            # test for a count of 0 following
            self.assertIn("0", found[2].text)
            # test for a count of 1 like
            self.assertIn("1", found[3].text)

    def test_add_like(self):
        m = Message(id=56765, text="Testing add like", user_id=self.user1_id)
        db.session.add(m)
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.post("/messages/56765/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id == 56765).all()
            self.assertEqual(len(likes), 1)
            self.assertEqual(likes[0].user_id, self.testuser_id)

    def test_remove_like(self):
        self.setup_likes()

        m = Message.query.filter(Message.text == "test message 3").one()
        self.assertIsNotNone(m)
        self.assertNotEqual(m.user_id, self.testuser_id)

        l = Likes.query.filter(
            Likes.user_id == self.testuser_id and Likes.message_id == m.id).one()

        self.assertIsNotNone(l)

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = c.post(f"/messages/{m.id}/like", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id == m.id).all()
            self.assertEqual(len(likes), 0)

    def test_unauthenticated_like(self):
        self.setup_likes()

        m = Message.query.filter(Message.text == "test message 3").one()
        self.assertIsNotNone(m)

        likes_count = Likes.query.count()

        with self.client as c:
            response = c.post(f"/messages/{m.id}/like", follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(likes_count, Likes.query.count())

    def setup_followers(self):
        f1 = Follows(user_being_followed_id=self.user1_id,
                     user_following_id=self.testuser_id)
        f2 = Follows(user_being_followed_id=self.user2_id,
                     user_following_id=self.testuser_id)
        f3 = Follows(user_being_followed_id=self.testuser_id,
                     user_following_id=self.user1_id)

        db.session.add_all([f1, f2, f3])
        db.session.commit()

    def test_user_show_with_follows(self):
        self.setup_followers()

        with self.client as c:
            response = c.get(f"/users/{self.testuser_id}")
            self.assertEqual(response.status_code, 200)

            self.assertIn("@testuser", str(response.data))
            soup = BeautifulSoup(str(response.data), 'html.parser')
            found = soup.find_all("li", {"class": "stat"})
            self.assertEqual(len(found), 4)
            self.assertIn("0", found[0].text)
            self.assertIn("1", found[2].text)
            self.assertIn("0", found[3].text)

    def test_show_following(self):

        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            response = c.get(f"/users/{self.testuser_id}/following")
            self.assertEqual(response.status_code, 200)
            self.assertIn("@user1", str(response.data))
            self.assertIn("@user2", str(response.data))
            self.assertNotIn("@user3", str(response.data))
            self.assertNotIn("@user4", str(response.data))

    def test_show_followers(self):

        self.setup_followers()
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            response = c.get(f"/users/{self.testuser_id}/followers")
            self.assertIn("@user1", str(response.data))
            self.assertNotIn("@user2", str(response.data))
            self.assertNotIn("@user3", str(response.data))
            self.assertNotIn("@user4", str(response.data))

    def test_unauthorized_following_page_access(self):
        self.setup_followers()
        with self.client as c:

            response = c.get(
                f"/users/{self.testuser_id}/following", follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("@user1", str(response.data))

    def test_unauthorized_followers_page_access(self):
        self.setup_followers()
        with self.client as c:

            response = c.get(
                f"/users/{self.testuser_id}/followers", follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("@user1", str(response.data))
