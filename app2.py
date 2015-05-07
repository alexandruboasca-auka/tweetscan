import sqlite3
import re

connection = sqlite3.connect('tweets.db')

class WordCount():
    
    def __init__(self, sterm):
        self.sterm = sterm
    
    def to_dict(self):
		t = (self.sterm,)
		for row in connection.execute('SELECT * FROM tweets WHERE sterm=? ORDER BY mentions', t):
			