""" Message Model Tests """

from app import app
import os
from unittest import TestCase
from sqlalchemy import exc

from models import db, User, Message, Follows, Likes

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


db.create_all()


class UserModelTestCase(TestCase):
    """ Test views for Messages """

    def setUp(self):
        """ Create test client and add Sample Data """
        db.drop_all()
        db.create_all()

        self.uid = 12345
        u = User.signup("test", "test@test.com", "password", None)
        u.id = self.uid
        db.session.commit()

        self.u = User.query.get(self.uid)
        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_message_model(self):
        """ Does message model work? """

        m = Message(
            text="new message",
            user_id=self.uid
        )

        db.session.add(m)
        db.session.commit()

        self.assertEqual(len(self.u.messages), 1)
        self.assertEqual(self.u.messages[0].text, "new message")

    def test_message_likes(self):
        m1 = Message(
            text="new message",
            user_id=self.uid
        )

        m2 = Message(
            text="next new message",
            user_id=self.uid
        )

        u = User.signup("test2", "test2@test.com", "password", None)
        uid = 4321
        u.id = uid
        db.session.add_all([m1, m2, u])
        db.session.commit()

        u.likes.append(m1)
        db.session.commit()

        l = Likes.query.filter(Likes.user_id == uid).all()
        self.assertEqual(len(l), 1)
        self.assertEqual(l[0].message_id, m1.id)
