from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash, Response, \
    make_response, jsonify
from jinja2 import Environment
import os

jinja_env = Environment(extensions=['jinja2.ext.with_'])

app = Flask(__name__)
app.config.from_object(__name__)
app.config['STATIC_FOLDER'] = os.getcwd()
cfg = None


@app.route('/', methods=['GET', 'POST'])
def show_entries():
    if request.method == 'POST':
        pass



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
