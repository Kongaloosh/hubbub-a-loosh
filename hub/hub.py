from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, \
    make_response, jsonify
from jinja2 import Environment
import os
import random
import requests
import string
import sqlite3
from werkzeug.exceptions import BadRequestKeyError

jinja_env = Environment(extensions=['jinja2.ext.with_'])

app = Flask(__name__)
app.config.from_object(__name__)
app.config['STATIC_FOLDER'] = os.getcwd()
cfg = None


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


def subscribe(hub_topic, hub_callback, hub_lease_seconds=None, hub_secret=None):
    #   if the topic is not yet in the dbms
    insert = ["\""+hub_topic+"\"", "\""+hub_callback+"\""]
    labels = "topic, callback"

    if hub_lease_seconds:                       # if there exists a lease, add it to the list of things committed
        insert.append(str(hub_lease_seconds))
        labels += ", lease"

    if hub_secret:                              # if there exists a secret, add it to the list of things committed
        insert.append("\""+hub_secret+"\"")
        labels += ', secret'

    cur = g.db.execute(
        """
        INSERT INTO subscribers
        ({0}) VALUES ({1});
        """.format(labels, ",".join(insert))
    )

    return make_response(("Subscription successful", 200))


def unsubscribe(hub_topic, hub_callback):
    cur = g.db.execute(
        """
        DELETE FROM subscribers
        WHERE "topic = '{0}' AND callback = '{1}'";
        """.format(hub_topic, hub_callback)
    )
    return make_response(("Unubscription successful", 200))


def verify(hub_callback, hub_mode, hub_topic, hub_lease_seconds=None, hub_secret=None, headers=None):
    """Verifies a request and performs an action if the verification is successful (subscribe/unsubscribe)"""
    challenge = challenge_me(30)      # generates a challenge string
    # the request we are sending to the callback tao verify the request
    payload = {
        'hub.mode': hub_mode,
        'hub.topic': hub_topic,
        'hub.challenge': challenge,
    }
    if hub_lease_seconds:
        payload['hub.lease_seconds'] = hub_lease_seconds

    resp_headers = {}
    result = requests.get(hub_callback, params=payload, headers=resp_headers)

    if result.json()['hub.challenge'] == challenge and int(result.status_code / 100) == 2:
        if hub_lease_seconds:
            return subscribe(hub_topic, hub_callback, hub_lease_seconds, hub_secret)
        else:
            return unsubscribe(hub_topic, hub_callback)
    return abort(404)


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


@app.route('/', methods=['GET', 'POST'])
def show_entries():
    """Hub which handles routing between the publisher and subscribers"""
    if request.method == 'POST':  # if we are recieving a post
        # try:
        #     request.headers['application/x-www-form-urlencoded ']  # check to make sure the headers are correct
        # except KeyError:
        #     abort(401)  # todo: better for malforming.

        app.logger.info(dir(request))
        app.logger.info((request.form, request.args))

        """ request must include"""
        try:
            hub_callback = request.form['hub.callback']
        except BadRequestKeyError:
            try:
                hub_callback = request.args['hub.callback']
            except BadRequestKeyError:
                abort(500)
        try:
            hub_mode = request.form['hub.mode']
        except BadRequestKeyError:
            try:
                hub_mode = request.args['hub.mode']
            except BadRequestKeyError:
                abort(500)

        try:
            hub_topic = request.form['hub.topic']
        except KeyError:
            try:
                hub_topic = request.args['hub.topic']
            except:
                abort

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

        app.logger.info((hub_secret,hub_lease_seconds,hub_topic,hub_callback,hub_mode))

        if hub_mode == 'subscribe':  # if this is a subscription, verify
            return verify(hub_callback=str(hub_callback), hub_mode=str(hub_mode), hub_topic=str(hub_topic),
                   hub_lease_seconds=str(hub_lease_seconds), hub_secret=hub_secret)
        elif hub_mode == 'unsubscribe':  # if this is an unsubscription, verify
            return verify(hub_callback=str(hub_callback), hub_mode=str(hub_mode), hub_topic=str(hub_topic),
                          headers=str(request.headers), hub_secret=hub_secret)
        elif hub_mode == 'list':
            pass
        elif hub_mode == 'retrieve':
            pass
        elif hub_mode == 'replay':
            pass


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
