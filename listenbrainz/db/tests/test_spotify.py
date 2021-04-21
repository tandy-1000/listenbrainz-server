# -*- coding: utf-8 -*-

import listenbrainz.db.user as db_user
import listenbrainz.db.spotify as db_spotify
import spotipy.oauth2
import sqlalchemy
import time

from datetime import datetime
from listenbrainz import db
from listenbrainz.db.testing import DatabaseTestCase
from unittest import mock
from unittest.mock import MagicMock


class SpotifyDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        super(SpotifyDatabaseTestCase, self).setUp()
        db_user.create(1, 'testspotifyuser')
        self.user = db_user.get(1)
        db_spotify.create_spotify(
            user_id=self.user['id'],
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )

    def test_create_spotify(self):
        db_user.create(2, 'spotify')
        db_spotify.create_spotify(
            user_id=2,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )
        token = db_spotify.get_token_for_user(2)
        self.assertEqual(token, 'token')

    def test_delete_spotify(self):
        token = db_spotify.get_token_for_user(self.user['id'])
        self.assertIsNotNone(token)
        db_spotify.delete_spotify(self.user['id'])
        token = db_spotify.get_token_for_user(self.user['id'])
        self.assertIsNone(token)

    def test_add_update_error(self):
        db_spotify.add_update_error(self.user['id'], 'test error message')
        spotify_user = db_spotify.get_user_import_details(self.user['id'])
        self.assertEqual(spotify_user['error_message'], 'test error message')
        self.assertIsNotNone(spotify_user['last_updated'])

    def test_update_last_updated(self):
        db_spotify.update_last_updated(self.user['id'])
        spotify_user = db_spotify.get_user(self.user['id'])
        self.assertIsNone(spotify_user['error_message'])
        self.assertIsNotNone(spotify_user['last_updated'])

    def test_update_token(self):
        old_spotify_user = db_spotify.get_user(self.user['id'])
        db_spotify.update_token(
            user_id=self.user['id'],
            access_token='testtoken',
            refresh_token='refreshtesttoken',
            expires_at=int(time.time()),
        )
        spotify_user = db_spotify.get_user(self.user['id'])
        self.assertEqual(spotify_user['access_token'], 'testtoken')
        self.assertEqual(spotify_user['refresh_token'], 'refreshtesttoken')

    def test_update_latest_listened_at(self):
        old_spotify_user = db_spotify.get_user(self.user['id'])
        self.assertIsNone(old_spotify_user['latest_listened_at'])
        t = int(time.time())
        db_spotify.update_latest_listened_at(self.user['id'], t)
        spotify_user = db_spotify.get_user(self.user['id'])
        self.assertEqual(t, int(spotify_user['latest_listened_at'].strftime('%s')))

    def test_get_active_users_to_process(self):
        db_user.create(2, 'newspotifyuser')
        db_spotify.create_spotify(
            user_id=2,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )
        users = db_spotify.get_active_users_to_process()
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0]['user_id'], 1)
        self.assertEqual(users[0]['musicbrainz_row_id'], 1)
        self.assertEqual(users[1]['user_id'], 2)
        self.assertEqual(users[1]['musicbrainz_row_id'], 2)

        # check order, the users should be sorted by latest_listened_at timestamp
        db_user.create(3, 'newnewspotifyuser')
        db_spotify.create_spotify(
            user_id=3,
            access_token='tokentoken',
            refresh_token='newrefresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )
        t = int(time.time())
        db_spotify.update_latest_listened_at(2, t + 20)
        db_spotify.update_latest_listened_at(1, t + 10)
        users = db_spotify.get_active_users_to_process()
        self.assertEqual(len(users), 3)
        self.assertEqual(users[0]['user_id'], 2)
        self.assertEqual(users[1]['user_id'], 1)
        self.assertEqual(users[2]['user_id'], 3)

        db_spotify.add_update_error(2, 'something broke')
        db_spotify.add_update_error(3, 'oops.')
        users = db_spotify.get_active_users_to_process()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['user_id'], 1)

    def test_get_user(self):
        user = db_spotify.get_user(self.user['id'])
        self.assertEqual(user['user_id'], self.user['id'])
        self.assertEqual(user['musicbrainz_id'], self.user['musicbrainz_id'])
        self.assertEqual(user['musicbrainz_row_id'], self.user['musicbrainz_row_id'])
        self.assertEqual(user['access_token'], 'token')
        self.assertEqual(user['refresh_token'], 'refresh_token')
        self.assertIn('last_updated', user)
        self.assertIn('latest_listened_at', user)
        self.assertIn('token_expires', user)
        self.assertIn('token_expired', user)
