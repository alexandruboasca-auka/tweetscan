import os, os.path
import re
import datetime
import json
import collections

import cherrypy

import tweepy
import sqlite3

ckey = ''
csecret = ''
atoken = ''
asecret = ''

with sqlite3.connect('tweets.db', check_same_thread=False) as connection:
    auth = tweepy.OAuthHandler(ckey, csecret)
    auth.set_access_token(atoken, asecret)
    
class WordCount():
    
    def __init__(self, sterm):
        self.sterm = sterm
    
    def to_dict(self):
        prep_stat = (self.sterm,)
        pattern = re.compile('[ ]\w{4,}')
        cursor = connection.cursor()
        for row in connection.execute('SELECT * FROM tweets WHERE sterm=?', prep_stat):
            match_word = re.findall(pattern, row[1].decode('utf-8'))
            for word in match_word:
                if (word.encode('utf-8') == 'http' or word.encode('utf-8') == 'https'):
                    continue
                prep_stat_two = (self.sterm, word.encode('utf-8').strip().lower(),)
                cursor.execute('SELECT * FROM terms WHERE sterm=? AND aterm=?', prep_stat_two)
                data = cursor.fetchone()
                if data is None:
                    prep_stat_three = (self.sterm, word.encode('utf-8').strip().lower(),datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
                    connection.execute('INSERT INTO terms (sterm, aterm, mentions, fmention) VALUES (?,?,1,?)', prep_stat_three)
                else:
                    connection.execute('UPDATE terms SET mentions = mentions + 1 WHERE sterm = ? AND aterm = ?', prep_stat_two)           
        connection.commit()
      
class OutListener(tweepy.StreamListener):
            
    def __init__(self, api=None):
        super(OutListener, self).__init__()
        self.num_tweets = 0
        self.sterm = ' '
        self.max_tweets = 0
    	
    def on_status(self, status):
        if (self.num_tweets <= self.max_tweets):
            to_insert = (self.sterm, status.text.encode('utf-8'), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            connection.execute('INSERT INTO tweets (sterm, tweet, date) VALUES (?,?,?)', to_insert)
            self.num_tweets += 1
            return True
        else:
            connection.commit()
            return False

    def on_error(self, status):
        print (status)
        return True

class MainApp(object):
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def display(self, search_term):
        objects_list = []
        prep_stat = (search_term,)
        counter = 0
        for row in connection.execute('SELECT * FROM terms WHERE sterm = ? ORDER BY mentions DESC', prep_stat):
            if counter > 30:
                break
            d = collections.OrderedDict()
            d['text'] = row[1].decode('utf-8')
            d['weight'] = row[2]
            objects_list.append(d)
            counter += 1
        j_data = json.dumps(objects_list)
        return j_data

    @cherrypy.expose
    def result(self, search_term):
        #listener = OutListener()
        #listener.sterm = search_term
        #listener.max_tweets = 50
        #twitterStream = tweepy.Stream(auth, listener)
        #twitterStream.filter(track=[search_term])
        wordc = WordCount(search_term)
        wordc.to_dict()
        return open('result.html')
        
    @cherrypy.expose
    def shutdown(self):
        cherrypy.engine.exit()
    
    @cherrypy.expose
    def index(self):
        return open('index.html')

if __name__ == '__main__':
	cherrypy.quickstart(MainApp(), '/', 'app.config')		

