from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, \
    make_response, jsonify
import hashlib
import hmac
from jinja2 import Environment
import logging
from logging import Formatter, FileHandler
import os
import random
import requests
from requests import ConnectionError
import string
import sqlite3
import threading
import time
import urllib
from werkzeug.exceptions import BadRequestKeyError

jinja_env = Environment(extensions=['jinja2.ext.with_'])

app = Flask(__name__)
app.config.from_object(__name__)
app.config['STATIC_FOLDER'] = os.getcwd()
cfg = None

gunicorn_error_logger = logging.getLogger('gunicorn.error')
app.logger.handlers.extend(gunicorn_error_logger.handlers)
app.logger.setLevel(logging.DEBUG)
app.logger.debug('this will show in the log')


def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('dbms/hub.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


def connect_db():
    return sqlite3.connect('hub/dbms/hub.db')


@app.before_request
def before_request():
    g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


def get_db():
    if 'db' not in g:
        g.db = connect_db()
    return g


@app.teardown_appcontext
def teardown_db(self):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def denial():
    response = make_response(topic, reason)
    response.args['hub.mode'] = 'denied'
    response.headers['hub.topic'] = topic
    response.status_code
    return


def challenge_me(n):
    """Generates a random challenge string for verification of length n
    Args:
        n: integer length of the challenge string
    Returns:
        challenge string of length n.
    """
    return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(n))


def publish(topic):
    g = get_db()
    cur = g.db.execute(
        """
        SELECT callback, secret
        FROM 'subscribers'
        WHERE topic = '{0}';
        """.format(topic)
    )
    results = cur.fetchall()

    response = requests.get(topic)

    for callback, secret in results:
        # print subscriber, secret
        if secret:
            paybytes = response.content
            app.logger.info(type(str.encode(secret)))
            sign = hmac.new(str.encode(secret), paybytes, hashlib.sha512).hexdigest()
            app.logger.info(sign)
            headers = {
                "X-Hub-Signature": 'sha512={0}'.format(sign),
                'content-type': response.headers['content-type'],
                'link': '<http://hub.kongaloosh.com/>; rel="hub", <{0}>; rel="self"'.format(topic)

            }
            try:
                requests.post(callback, headers=headers, data=response.content)
            except ConnectionError:
                pass
        else:
            app.logger.info(response.headers['content-type'])
            headers = {
                'content-type': response.headers['content-type'],
                'link': '<http://hub.kongaloosh.com/>; rel="hub", <{0}>; rel="self"'.format(topic),
            }
            try:
                app.logger.info('posting to: {0}'.format(callback))
                r = requests.post(callback, data=response.content, headers=headers)
            except ConnectionError:
                pass
    return make_response(("notifying subscribers", 200))


def subscribe(hub_topic, hub_callback, g, hub_lease_seconds=None, hub_secret=None):
    #   if the topic is not yet in the dbms
    g = get_db()
    insert = ["\"" + hub_topic + "\"", "\"" + hub_callback + "\""]
    labels = "topic, callback"

    if hub_lease_seconds:  # if there exists a lease, add it to the list of things committed
        insert.append(str(hub_lease_seconds))
        labels += ", lease"

    if hub_secret:  # if there exists a secret, add it to the list of things committed
        insert.append("\"" + hub_secret + "\"")
        labels += ', secret'
    g.db.execute(
        """
        INSERT INTO subscribers
        ({0}) VALUES ({1});
        """.format(labels, ",".join(insert))
    )
    g.db.commit()


def unsubscribe(hub_topic, hub_callback, g):
    g.db.execute(
        """
        DELETE FROM subscribers
        WHERE "topic = '{0}' AND callback = '{1}'";
        """.format(hub_topic, hub_callback)
    )
    g.db.commit()


def verify(hub_callback, hub_mode, hub_topic, g, hub_lease_seconds=None, hub_secret=None, headers=None):
    """Verifies a request and performs an action if the verification is successful (subscribe/unsubscribe)"""
    challenge = challenge_me(30)  # generates a challenge string
    # the request we are sending to the callback tao verify the request
    payload = {
        'hub.mode': hub_mode,
        'hub.topic': hub_topic,
        'hub.challenge': challenge,
    }
    if hub_lease_seconds:
        payload['hub.lease_seconds'] = hub_lease_seconds

    resp_headers = {}
    try:
        result = requests.get(hub_callback, params=payload, headers=resp_headers)
    except ConnectionError:
        app.logger.error("Connection Error: Verification Request Incomplete: {0}".format(result.text))

    try:
        challenge_check = result.json()['hub.challenge']
    except ValueError:
        challenge_check = result.content.decode("utf-8")

    if challenge_check == challenge and int(result.status_code / 100) == 2:
        if hub_mode == "subscribe":
            with app.app_context():
                subscribe(hub_topic=hub_topic, hub_callback=hub_callback, hub_lease_seconds=hub_lease_seconds,
                          hub_secret=hub_secret, g=g)
        else:
            with app.app_context():
                unsubscribe(hub_topic, hub_callback, g)


@app.route('/', methods=['GET', 'POST'])
def show_entries():
    """Hub which handles routing between the publisher and subscribers"""
    if request.method == 'POST':  # if we are recieving a post
        """ request must include"""
        try:
            hub_callback = request.form['hub.callback']
        except BadRequestKeyError:
            try:
                hub_callback = request.args['hub.callback']
            except BadRequestKeyError:
                pass
        try:
            hub_mode = request.form['hub.mode']
        except BadRequestKeyError:
            try:
                hub_mode = request.args['hub.mode']
            except BadRequestKeyError:
                pass

        try:
            hub_topic = request.form['hub.topic']
        except KeyError:
            try:
                hub_topic = request.args['hub.topic']
            except BadRequestKeyError:
                hub_topic = None

        try:
            hub_url = request.form['hub.url']
        except KeyError:
            try:
                hub_url = request.args['hub.url']
            except KeyError:
                hub_url = None

        try:
            hub_secret = request.form['hub.secret']
        except KeyError:
            try:
                hub_secret = request.args['hub.secret']
            except BadRequestKeyError:
                hub_secret = None
        try:
            hub_lease_seconds = request.args['hub.lease_seconds']
        except KeyError:
            if hub_mode == 'subscribe':  # if there is no lease specified during subscription, make the lease 10 days
                hub_lease_seconds = 10 * 60 * 60 * 24
            else:  # otherwise no lease is required for the request
                hub_lease_seconds = None
        if hub_mode == 'subscribe':  # if this is a subscription, verify
            app.logger.debug("verifying with thread {0} \n {1}".format(verify, {
                'hub_callback': str(hub_callback),
                'hub_mode': str(hub_mode),
                'hub_topic': str(hub_topic),
                'hub_lease': str(hub_lease_seconds),
                'hub_secret': hub_secret
            }))
            with app.app_context():
                t = threading.Thread(
                    target=verify,
                    kwargs={
                        'hub_callback': str(hub_callback),
                        'hub_mode': str(hub_mode),
                        'hub_topic': str(hub_topic),
                        'hub_lease_seconds': hub_lease_seconds,
                        'hub_secret': hub_secret,
                        'g': g
                    }
                )
                t.start()
            return make_response(("Subscription is being queued for verification.", 202))

        elif hub_mode == 'unsubscribe':  # if this is an unsubscription, verify
            with app.app_context():
                t = threading.Thread(
                    target=verify,
                    kwargs={'hub_callback': str(hub_callback),
                            'hub_mode': str(hub_mode),
                            'hub_topic': str(hub_topic),
                            'headers': str(request.headers),
                            'hub_secret': hub_secret,
                            'g': g}
                )
                t.start()
            return make_response(("Unsubscription is being queued for verification.", 202))
        elif hub_mode == 'list':
            abort(404)
        elif hub_mode == 'retrieve':
            abort(404)
        elif hub_mode == 'replay':
            abort(404)
        elif hub_mode == 'publish':
            app.logger.info(
                (hub_url, hub_topic)
            )
            if hub_url:
                return publish(hub_url)
            elif hub_topic:
                return publish(hub_topic)
            return abort(404)


@app.route('/login')
def login():
    if session.get('logged_in'):
        pass  # todo: login template
    else:
        abort(401)


@app.route('/logout')
def logout():
    if session.get('logged_in'):
        pass
    else:
        abort(401)


@app.route('/dashboard')
def dashboard():
    pass


if __name__ == "__main__":
    if not os.path.isfile('hub/dbms/hub.db'):
        print("Creating DBMS!")
        init_db()

    app.run(debug=True)
