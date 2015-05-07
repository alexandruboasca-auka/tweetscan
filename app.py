import cherrypy

import re

import tweepy
import sqlite3

ckey = 'T8Poz8mbJ0MNHhBkRdnZ5pob4'
csecret = 'nVGDX6ni63kDVkHiIReM9snsSWhlJnGDpOk2ah8tOdrCA1DYD5'
atoken = '3130785886-JpEqFnloPNmmpOFri54g7aEjkKKMVuQUAI4sKKA'
asecret = '0efgtCpv18aoXzcXzBs8YCejimYVC63XlZUYgk77YlySw'

with sqlite3.connect('tweets.db', check_same_thread=False) as connection:
    auth = tweepy.OAuthHandler(ckey, csecret)
    auth.set_access_token(atoken, asecret)
    #twitterStream = tweepy.Stream(auth, OutListener())
    #twitterStream.filter(track=["rihanna"])
        
class OutListener(tweepy.StreamListener):
            
    def __init__(self, api=None):
        super(OutListener, self).__init__()
        self.num_tweets = 0
        self.sterm = ' '
        self.max_tweets = 0
    	
    def on_status(self, status):
        if (self.num_tweets <= self.max_tweets):
            to_insert = (self.sterm, status.text.encode('utf-8'),)
            connection.execute('INSERT INTO tweets (sterm, tweet) VALUES (?,?)', to_insert)
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
    def search(self, search_term):
        listener = OutListener()
        listener.sterm = search_term
        listener.max_tweets = 50
        twitterStream = tweepy.Stream(auth, listener)
        twitterStream.filter(track=[search_term])
        return '''
    done
    '''

    @cherrypy.expose
    def shutdown(self):
        cherrypy.engine.exit()
    
    @cherrypy.expose
    def index(self):
        return '''
		<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Document</title>
    <link rel="stylesheet" href="css/style.css">
    <link rel="stylesheet" href="css/font-awesome.min.css">
    <link href='http://fonts.googleapis.com/css?family=Open+Sans' rel='stylesheet' type='text/css'>
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.4/jquery.min.js"></script>
</head>
<body>

    <div class="header_container"> 
            <header class="main_header">TWords</header>
    </div>

    <div class="search_container"> 
        <form method="get" action="search">
           <i id="settings_cog" class="fa fa-cog fa-5x"></i>
            <input type="text" name="search_term" class="search_input" autofocus>
            <i id="enter_arrow" class="fa fa-arrow-right fa-5x"></i>
        </form> 
    </div>

    <div id="sett_cont" class="settings_container">

    </div>

    <script>
        $( "#settings_cog" ).click(function() {
            $( "#sett_cont" ).slideToggle();  
        });
    </script>

    <a id="shutdown"; href="./shutdown">Shutdown Server</a>
</body>
</html>
		'''

if __name__ == '__main__':
	cherrypy.quickstart(MainApp(), '/', 'app.config')		

