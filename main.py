from flask import Flask, request, session, redirect, url_for, render_template, flash

import os, sys, time, hashlib
import json
import requests

from oauth2 import OAuth2

app = Flask(__name__)

RENREN_APP_ID = '694b311a3d7b4e1888ab183ed971fb6a'
RENREN_APP_SECRET = 'a4a36d28d3ae4804b79fd742728a40fd'
# base url
BASE_URL = 'http://api.renren.com/restserver.do?'

oauth2_handler = OAuth2(RENREN_APP_ID, RENREN_APP_SECRET, "https://graph.renren.com/", "http://example.com/renrencallback", "oauth/authorize", "oauth/token")

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error.html'), 404

@app.errorhandler(505)
def internal_error(error):
    return render_template('error.html'), 505

@app.route('/logout', methods=['GET'])
def logout():
    #remove access_token from the session if it's there
    session.pop('access_token', None)
    return redirect(url_for('index'))

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/renrenauth', methods=['GET'])
def renren_auth():
    authorization_url = oauth2_handler.authorize_url(response_type='code', scope='read_user_status read_user_blog read_user_album')
    print authorization_url

    return redirect(authorization_url)

@app.route('/renrencallback', methods=['GET'])
def renren_callback():
    error = request.args.get('error', None)
    if error:
        flash("authorizaton error")
        return redirect(url_for('index'))
    code = request.args.get('code', None)
    print code
    if code is None:
        flash("login error, please try again")
        return redirect(url_for('index'))
    response = oauth2_handler.get_token(code, grant_type='authorization_code')
    access_token = response['access_token']
    print access_token
    session['access_token'] = access_token
    return redirect(url_for('vis_friends'))

@app.route('/vis', methods=['GET'])
def vis_friends():
    json_data = combine_data()
#    with open('data.json', 'w') as outfile:
 #       json.dump(data, outfile)

    return render_template('vis.html', data = json_data)

def get_user_info(method='users.getInfo', v='1.0', format='json'):
    call_id = str(int(time.time()*1000))
    
    params = {
        'access_token': session['access_token'],
        'v': v,
        'method': method,
        'call_id': call_id,
        'format': format
        }
    # compute sig
    sig = get_sig(params)
    params.update({'sig': sig})
    url = concat_url(params)
    response = requests.post(url)
    return response.text
    
def get_friends_list( method='friends.getFriends', v='1.0', format='json'):
    call_id = str(int(time.time()*1000))
    
    params = {
        'access_token': session['access_token'],
        'v': v,
        'method': method,
        'call_id': call_id,
        'format': format
        }
    # compute sig
    sig = get_sig(params)
    params.update({'sig': sig})
    url = concat_url(params)
    response = requests.post(url)
    return response.text

def combine_data():
    user_info = json.loads(get_user_info())[0]
    uid = user_info['uid']
    uname = user_info['name']
    uhead = user_info['headurl']
    nodes = []
    links = []
    target = 1
    nodes.append({"id": uid, "name": uname, "head": uhead})
    friends_list = json.loads(get_friends_list())
    for friend in friends_list:
        nodes.append({"id": friend['id'], "name": friend['name'], "head": friend['headurl']})
        links.append({"source": 0, "target": target})
        target = target + 1
    
    json_data = {"nodes": nodes, "links": links}
    return json_data

# Detect if a string is unicode and encode as utf-8
def unicode_encode(str):
    return isinstance(str, unicode) and str.encode('utf-8') or str

def get_sig(params):
    message =''.join(['%s=%s' % (unicode_encode(k),unicode_encode(v)) for (k,v) in sorted(params.iteritems())])
    m=hashlib.md5(message+RENREN_APP_SECRET)
    sig=m.hexdigest()
    return sig

def concat_url(params):
    url ='&'.join(['%s=%s' % (unicode_encode(k),unicode_encode(v)) for (k,v) in params.iteritems()])
    return BASE_URL+url

# set the secret key
app.secret_key = os.urandom(24)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
