from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, \
    make_response, jsonify
from jinja2 import Environment
import os
import requests

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
   return ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(n))


def subscribe():
    pass


def unsubscribe():
    pass


def verify(hub_callback, hub_mode, hub_topic, hub_lease_seconds=None):
    challenge = challenge_me()
    payload = {
        'hub.mode': hub_mode,
        'hub.topic': hub_topic,
        'hub.challenge': challenge,
    }
    if hub_lease_seconds:
        payload['hub.lease_seconds']=hub_lease_seconds

    result = requests.get(hub_callback, params=payload, headers=headers, status_code=status_code)

    if result.json['hub.challenge'] == challenge and int(result.status_code/100) == 2:
        if hub_lease_seconds:
            subscribe()
        else:
            unsubscribe()
    return abort(404)



@app.route('/', methods=['GET', 'POST'])
def show_entries():
    if request.method == 'POST':
        try:
            request.headers['application/x-www-form-urlencoded ']
        except KeyError:
            abort(401)  # todo: better for malforming.

        """ request must include"""
        try:
            hub_callback = request.args['hub.callback']
        except KeyError:
            abort
        try:
            hub_mode = request.args['hub.mode']
        except KeyError:
            abort

        try:
            hub_topic = request.args['hub.topic']
        except KeyError:
            abort

        try:
            hub_secret = request.args['hub.secret']
        except KeyError:
            abort

        try:
            hub_lease_seconds = request.args['hub.lease_seconds']
        except KeyError:
            if hub_mode == 'subscribe':
                hub_lease_seconds = 10*60*60*24
            else:
                hub_lease_seconds = None


        if hub_mode == 'subscribe':
            verify(hub_callback=hub_callback, hub_mode=hub_mode, hub_topic=hub_topic, hub_lease_seconds=hub_lease_seconds)
        elif hub_mode == 'unsubscribe':
            verify(hub_callback=hub_callback, hub_mode=hub_mode,hub_topic=hub_topic)
        elif hub_mode == 'list':
            pass
        elif hub_mode == 'retrieve':
            pass
        elif hub_mode == 'replay':
            pass

        return response


@app.route('/login')
def login():
    if session.get('logged_in'):
        pass # todo: login template
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
    app.run(debug=True)
