from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, \
    make_response, jsonify
from jinja2 import Environment
import os
import requests
from werkzeug.exceptions import BadRequestKeyError

jinja_env = Environment(extensions=['jinja2.ext.with_'])

app = Flask(__name__)
app.config.from_object(__name__)
app.config['STATIC_FOLDER'] = os.getcwd()
cfg = None

@app.route('/', methods=['GET', 'POST'])
def show_entries():
    if request.method == 'POST':
        pass

    if request.method == 'GET':
        payload = {}
        try:
            payload = {
                'hub.challenge': request.form['hub.challenge'],
            }
        except BadRequestKeyError:
                payload = {
                   'hub.challenge': request.args['hub.challenge']
                }
        except BadRequestKeyError:
            app.logger.info(request)
        response = make_response((jsonify(payload), 200))
        app.logger.info(response)
        return response

@app.route('/ping')
def ping():
    payload = {
        'hub.mode': 'subscribe',
        'hub.topic': 'http://127.0.0.1:5000/',
        'hub.callback': 'http://127.0.0.1:8000/'
    }
    r = requests.post(payload['hub.topic'], params=payload, headers={})
    app.logger.info(r)

if __name__ == "__main__":
    app.run(debug=True, port=8000)
