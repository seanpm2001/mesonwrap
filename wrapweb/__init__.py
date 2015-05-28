# Copyright 2015 The Meson development team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from flask import Flask, jsonify, request, Response, g
import re, os
import wrapdb
import wrapdb, wrapupdater

app = Flask(__name__)

db_directory = os.path.normpath(os.path.join(os.path.split(__file__)[0], '..'))

def get_query_db():
    db = getattr(g, '_query_database', None)
    if db is None:
        db = g._query_database = wrapdb.WrapDatabase(db_directory)
    return db

def get_update_db():
    db = getattr(g, '_update_database', None)
    if db is None:
        db = g._update_database = wrapupdater.WrapUpdater(db_directory)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_query_database', None)
    if db is not None:
        db.close()
    db = getattr(g, '_update_database', None)
    if db is not None:
        db.close()

def get_projectlist():
    querydb = get_query_db()
    res = {'output' : 'ok', 'projects' : querydb.name_search('')}
    return jsonify(res)

@app.route("/projects", defaults={"project": None})
@app.route("/projects/<project>")
def get_project_info(project):
    if project is None:
        return get_projectlist()
    querydb = get_query_db()
    matches = querydb.get_versions(project)

    if len(matches) == 0:
        out = {"output": "notok", "error": 'No such project'}
        jsonout = jsonify(out)
        jsonout.status_code = 500
        return jsonout

    out = {"output": "ok", "versions": []}
    for i in matches:
        e = {'branch': i[0], 'revision' : i[1]}
        out['versions'].append(e)
    jsonout = jsonify(out)
    jsonout.status_code = 200
    return jsonout

@app.route("/projects/<project>/get_wrap", methods=['GET'])
@app.route("/projects/<project>/get_zip", methods=['GET'])
def get_wrap(project):
    querydb = get_query_db()
    branch=request.args["branch"]
    revision=int(request.args["revision"])
    if request.path.endswith("/get_wrap"):
        result = querydb.get_wrap(project, branch, revision)
        mtype = 'text/plain'
    else:
        result = querydb.get_zip(project, branch, revision)
        mtype = 'application/zip'
    if result is None:
        out = {"output": "notok", "error": "No such entry"}
        jsonout = jsonify(out)
        jsonout.status_code = 500
        return jsonout
    else:
        return Response(result, mimetype=mtype)

# Change to match whatever github expects to get. Also verify password/IP/whatever.
@app.route('/update/<project>/<branch>')
def update_project(project, branch):
    # pwdfile = os.path.join(db_directory, 'password.txt')
    # password = open(pwdfile).read().strip()
    if not re.fullmatch('[a-z0-9._]+', project):
        out = {"output": "notok", "error": "Invalid project name"}
        jsonout = jsonify(out)
        jsonout.status_code = 500
        return jsonout
    if not re.fullmatch('[a-z0-9._]+', branch):
        out = {"output": "notok", "error": "Invalid branch name"}
        jsonout = jsonify(out)
        jsonout.status_code = 500
        return jsonout
    if branch == 'master':
        out = {"output": "notok", "error": "No bananas for you"}
        jsonout = jsonify(out)
        jsonout.status_code = 500
        return jsonout
    db_updater = get_update_db()
    repo_url = 'https://github.com/mesonbuild/%s.git' % project
    # FIXME, should launch in the background instead. This will now block
    # until branching is finished.
    try:
        db_updater.update_db(project, repo_url, branch)
    except Exception:
        out = {"output": "notok", "error": "Wrap generation failed."}
        jsonout = jsonify(out)
        jsonout.status_code = 500
        return jsonout
    return jsonify({'output': 'ok'})
