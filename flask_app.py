
import os
import json
import sqlite3
import httplib2
import requests
import random

from time import sleep
from flask import Flask, request, session, g, redirect, url_for, render_template, flash, abort

#------------------------ GOOGLE NLP API setup ---------------------------#
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

credentials = GoogleCredentials.get_application_default()
scoped_credentials = credentials.create_scoped(['https://www.googleapis.com/auth/cloud-platform'])
http = httplib2.Http()
scoped_credentials.authorize(http)
service = discovery.build('language', 'v1beta1', http=http)
#----------------------- END of GOOGLE NLP API setup ---------------------#

app = Flask(__name__)
app.config.from_object(__name__)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'mock_exam.db'),
    SECRET_KEY='development key',
    USERNAME='yourUsername',
    PASSWORD='yourPassword'
))
app.config.from_envvar('GOOGLE_NLP_SETTINGS', silent=True)


#---------------------- START of Database Config -------------------------#
def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.cli.command('initdb')
def initdb_command():
    init_db()
    print('Initialized the database')
#----------------------- END of Database Config --------------------------#

#------------------------ START of API Calls -----------------------------#
def api_request(paragraph):

    requestBody = {
        "document": {
            "type": "PLAIN_TEXT",
            "content": paragraph
        },
        "features": {
            "extractSyntax": True,
            "extractEntities": True,
            "extractDocumentSentiment": True
        },
        "encodingType":"UTF8"
    }

    request = service.documents().annotateText(body=requestBody)

    analysis = request.execute()
    tokens = analysis.get('tokens', [])
    entities = analysis.get('entities', [])

    questions = []

    for triple in find_triples(tokens):
        questions.append(generate_question(show_triple(tokens, paragraph, triple), entities))

    return questions


def call_words_api(word, param):
    url = 'https://wordsapiv1.p.mashape.com/words/' + word + '/' + param
    headers = {
      "X-Mashape-Key": "yourAlphanumericKeyOfAbout50characters",
      "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)

    return response.json()

#-------------------------- END of API Calls -----------------------------#

#--------------------  Natural Language Processing  ----------------------#
def dependents(tokens, head_index):
    """Returns an ordered list of the token indices of the dependents for
    the given head."""
    # Create head->dependency index.
    head_to_deps = {}
    for i, token in enumerate(tokens):
        head = token['dependencyEdge']['headTokenIndex']
        if i != head:
            head_to_deps.setdefault(head, []).append(i)
    return head_to_deps.get(head_index, ())


def phrase_text_for_head(tokens, text, head_index):
    """Returns the entire phrase containing the head token
    and its dependents.
    """
    begin, end = phrase_extent_for_head(tokens, head_index)
    return text[begin:end]


def phrase_extent_for_head(tokens, head_index):
    """Returns the begin and end offsets for the entire phrase
    containing the head token and its dependents.
    """
    begin = tokens[head_index]['text']['beginOffset']
    end = begin + len(tokens[head_index]['text']['content'])
    for child in dependents(tokens, head_index):
        child_begin, child_end = phrase_extent_for_head(tokens, child)
        begin = min(begin, child_begin)
        end = max(end, child_end)
    return (begin, end)


def show_triple(tokens, text, triple):
    """Prints the given triple (left, head, right).  For left and right,
    the entire phrase headed by each token is shown.  For head, only
    the head token itself is shown.

    """
    nsubj, verb, dobj = triple

    # Extract the text for each element of the triple.
    nsubj_text = phrase_text_for_head(tokens, text, nsubj)
    verb_text = tokens[verb]['text']['content']
    dobj_text = phrase_text_for_head(tokens, text, dobj)

    sentence = [nsubj_text, verb_text, dobj_text]

    return sentence


def find_triples(tokens,
                 left_dependency_label='NSUBJ',
                 head_part_of_speech='VERB',
                 right_dependency_label='DOBJ'):
    """Generator function that searches the given tokens
    with the given part of speech tag, that have dependencies
    with the given labels.  For each such head found, yields a tuple
    (left_dependent, head, right_dependent), where each element of the
    tuple is an index into the tokens array.
    """
    for head, token in enumerate(tokens):
        if token['partOfSpeech']['tag'] == head_part_of_speech:
            children = dependents(tokens, head)
            left_deps = []
            right_deps = []
            for child in children:
                child_token = tokens[child]
                child_dep_label = child_token['dependencyEdge']['label']
                if child_dep_label == left_dependency_label:
                    left_deps.append(child)
                elif child_dep_label == right_dependency_label:
                    right_deps.append(child)
            for left_dep in left_deps:
                for right_dep in right_deps:
                    yield (left_dep, head, right_dep)


def generate_question(sentence, entities):
    x = random.randint(0, 2)    # endpoints included => 0, 1, 2

    ans = "no answer"
    question = "no question"
    wrongs = []
    target = "UNKNOWN"

    if (x == 0):
        ans = sentence[0]
        question = "Who/What " + sentence[1] + " " + sentence[2] + "?"

        for entity in entities:
            if entity["name"] == ans:
                target = entity["type"]
                break

        for entity in entities:
            if entity["type"] == target and entity["name"] != ans:
                wrongs.append(entity["name"])
                if len(wrongs) >= 3:
                    break

    elif (x == 1):
        ans = sentence[1]
        question = sentence[0] + " ___________________ " + sentence[2] + "."

        wrongs = call_words_api(ans, "rhymes")

        if (len(wrongs["rhymes"]) == 0):
            wrongs = call_words_api(ans, "antonyms")
            wrongs = wrongs["antonyms"]
        else:
            wrongs = wrongs["rhymes"]["all"]

    elif (x == 2):
        ans = sentence[2]
        question = sentence[0] + " " + sentence[1] + " _____________________ ."

        for entity in entities:
            if entity["name"] == ans:
                target = entity["type"]
                break
        for entity in entities:
            if entity["type"] == target and entity["name"] != ans:
                wrongs.append(entity["name"])
                if len(wrongs) >= 3:
                    break

    while (len(wrongs) < 3):
        wrongs.append("wrong-ans")

    p = [ans, wrongs[0], wrongs[1], wrongs[2]]
    random.shuffle(p)

    return [ question, p[0], p[1], p[2], p[3] ]
#-------------------- END of Natural Language Processing -----------------#

#---------------------- START of Application Routing ---------------------#
@app.route('/', methods=['GET'])
def home():
    # db = get_db()
    # cur = db.execute('select * from quiz order by id desc')
    # quiz = cur.fetchall()

    return render_template('home.html')


@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if not session.get('logged_in'):
        abort(401)
    db = get_db()
    # hold = call_words_api("love", "rhymes")["rhymes"]["all"];
    questions = api_request(request.form['user-text'])
    # questions = [["Who is the current president of the U.S?", "Obama", "Putin", "Biden", hold[0]], ["What year are we in?", "2016", "2009", hold[1], "3000"], ["Africa is a _____________", "continent", "desert", "country", hold[2]]]

    for q in questions:
        db.execute('insert into quiz (question, answer) values (?, ?)', [q[0], q[1]])
        db.commit()

    ans = []

    for i in range(len(questions)):
        ans.append(questions[i][1])

    return render_template('quiz.html', questions=questions, answers=ans)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('home'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('home'))


@app.route('/clear_quiz')
def clear_quiz():
    db = get_db()
    db.execute('delete from quiz')
    db.commit()

    return redirect(url_for('home'))
#------------------- END of Application's Routing ------------------------#
