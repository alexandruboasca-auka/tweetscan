import os, os.path
import re
import datetime
import json
import collections

import cherrypy

import tweepy
import sqlite3

#Twitter API credentials
ckey = 'T8Poz8mbJ0MNHhBkRdnZ5pob4'
csecret = 'nVGDX6ni63kDVkHiIReM9snsSWhlJnGDpOk2ah8tOdrCA1DYD5'
atoken = '3130785886-JpEqFnloPNmmpOFri54g7aEjkKKMVuQUAI4sKKA'
asecret = '0efgtCpv18aoXzcXzBs8YCejimYVC63XlZUYgk77YlySw'

#Global constants
DELETE_TIME_SECONDS = 300
MAX_TWEETS = 100
JSON_MAX = 30



#Connect to the Twitter API
with sqlite3.connect('tweets.db', check_same_thread=False) as connection:
    auth = tweepy.OAuthHandler(ckey, csecret)
    auth.set_access_token(atoken, asecret)
    
#The class WordProcces handles all the string manipulation.
class WordProcess():

    #Constructor takes a search term argument.
    def __init__(self, sterm):
        self.sterm = sterm
    
    #Searches the tweets in the DB, inserts all the associated words and counts the mentions of each word.
    def find_terms(self):
        #Excluded words list **NOT WORKING**
        excluded_words = ['http', 'https']
        #Prepared statement with the search term from the user.
        prep_stat = (self.sterm,)
        #Compile the regex for matching only the desired terms words.
        pattern = re.compile('[ ]\w{4,}')
        cursor = connection.cursor()
        #Select the tweets that match the search term.
        for row in connection.execute('SELECT * FROM tweets WHERE sterm=?', prep_stat):
            #Run the tweet through the regex.
            match_word = re.findall(pattern, row[2].decode('utf-8'))
            #Iterate through each word
            for word in match_word:
                encoded_word = word.encode('utf-8').strip().lower()
                #Check the word against the excluded words **NOT WORKING**
                if (encoded_word in excluded_words):
                    continue
                #Prepared statement with the word matched.
                prep_stat_two = (self.sterm, encoded_word,)
                #Execute the query.
                cursor.execute('SELECT * FROM terms WHERE sterm=? AND aterm=?', prep_stat_two)
                data = cursor.fetchone()
                #Check to see if the term is already in the DB. If it is, increment the no of mention. If not, insert it.
                if data is None:
                    prep_stat_three = (self.sterm, encoded_word, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),)
                    connection.execute('INSERT INTO terms (sterm, aterm, mentions, fmention) VALUES (?,?,1,?)', prep_stat_three)
                else:
                    connection.execute('UPDATE terms SET mentions = mentions + 1 WHERE sterm = ? AND aterm = ?', prep_stat_two)           
        #Commit the changes.            
        connection.commit()
    
    #Cleans up old tweets and terms.
    def clean_up(self):
        #Select * from tweets.
        for row in connection.execute('SELECT * FROM tweets'):
            #If the date-time of the tweet is older than [DELETE_TIME_SECONDS] then delete it.
            if ((datetime.datetime.now() - datetime.timedelta(seconds=DELETE_TIME_SECONDS)) > datetime.datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S")):
                prep_stat = (row[0],)
                connection.execute('DELETE FROM tweets WHERE id=?', prep_stat)
        #Select * from terms.
        for row in connection.execute('SELECT * FROM terms'):
            #If the first mention of the term is older [DELETE_TIME_SECONDS] then delete it.
            if ((datetime.datetime.now() - datetime.timedelta(seconds=DELETE_TIME_SECONDS)) > datetime.datetime.strptime(row[4], "%Y-%m-%d %H:%M:%S")):
                prep_stat = (row[0],)
                connection.execute('DELETE FROM terms WHERE id=?', prep_stat)
        #Commit the changes.
        connection.commit()
      
#Tweepy class, handles the Twitter API functions.      
class OutListener(tweepy.StreamListener):
            
    #No argument constructor, initializes the current tweet iterator and the max no of tweets.        
    def __init__(self, api=None):
        super(OutListener, self).__init__()
        self.num_tweets = 0
        self.sterm = ' '
        self.max_tweets = 0
    
    #Gets called on a new tweet.
    def on_status(self, status):
        #Check the current no of tweets iterator against the max tweets number.
        if (self.num_tweets <= self.max_tweets):
            #Prepared statement with the text of the tweet and the current date.
            to_insert = (self.sterm, status.text.encode('utf-8'), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            #Insert into the DB.
            connection.execute('INSERT INTO tweets (sterm, tweet, dateof) VALUES (?,?,?)', to_insert)
            #Increment the iterator.
            self.num_tweets += 1
            #Return True, keeps the stream open.
            return True
        else:
            #If the desired number is reached, commit the changed and close the stream.
            connection.commit()
            return False

    #Print the status on error and keep the stream open.        
    def on_error(self, status):
        print (status)
        return True

#The class of the app, contains the pages.
class MainApp(object):

    #Creates a JSON object from the entries in the DB.
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def display(self, search_term):
        #Create an empty list.
        objects_list = []
        #Prepared statement with the search term.
        prep_stat = (search_term,)
        #Initialize a counter, as we only care about the first [JSON_MAX].
        counter = 0
        for row in connection.execute('SELECT * FROM terms WHERE sterm = ? ORDER BY mentions DESC', prep_stat):
            #Check the counter, break if it passes.
            if counter >= JSON_MAX:
                break
            #Create a dictionary.
            d = collections.OrderedDict()
            #Add the values to the collection.
            d['text'] = row[2].decode('utf-8')
            d['weight'] = row[3]
            #Add the collection to the list.
            objects_list.append(d)
            #Increment counter
            counter += 1
        #Create a JSON object from the list and return it.
        j_data = json.dumps(objects_list)
        return j_data

    #The result page. **TO DO: Split it in two pages, (1)search and (2)result so the result
    #page can be refreshed without the query starting up again.**
    @cherrypy.expose
    def result(self, search_term):
        #Create the tweepy listener object.
        listener = OutListener()
        #Set the search term and the max no of tweets.
        listener.sterm = search_term
        listener.max_tweets = MAX_TWEETS
        #Create a stream object.
        twitterStream = tweepy.Stream(auth, listener)
        #Filter the search term.
        twitterStream.filter(track=[search_term])
        #Create a WordProcess object.
        wordp = WordProcess(search_term)
        #Clean old entries.
        wordp.clean_up()
        #Apply the search functions.
        wordp.find_terms()
        #Display the result.
        return open('result.html')
        
    @cherrypy.expose
    def shutdown(self):
        cherrypy.engine.exit()
    
    @cherrypy.expose
    def index(self):
        return open('index.html')

if __name__ == '__main__':
    cherrypy.config.update(
    {'server.socket_host': '0.0.0.0'} )
    cherrypy.quickstart(MainApp(), '/', 'app.config')
