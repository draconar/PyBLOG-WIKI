#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
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
#

import os
import webapp2
import jinja2
from google.appengine.ext import db
import logging
import json
from google.appengine.api import memcache
from datetime import datetime
from datetime import timedelta
import time

template_dir=os.path.join(os.path.dirname(__file__),'templates')
jinja_env=jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),autoescape=True)

## creating database
class Page(db.Model):
    name=db.StringProperty(required=True)
    content=db.TextProperty(required=True)
    created=db.DateTimeProperty(auto_now_add=True)
    last_modified=db.DateTimeProperty(auto_now = True)   
    

class User(db.Model):
    username = db.StringProperty(required = True)
    password = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class Handler(webapp2.RequestHandler):
    a="Happy"
    def write(self, *a,**kw):

        self.response.out.write(*a,**kw)
    def render_str(self,template,**params):
        t=jinja_env.get_template(template)

        return t.render(params)
    def render(self,template,**kw):
        a="Happy"
        self.write(self.render_str(template,**kw))

### BLOG STUFF
def wiki_key(name = 'default'):
  return db.Key.from_path('pages', name)


class SignUp(Handler):
  logging.info(Handler.a)
  
  def render_front(self,user="",email="", error=""):        
        self.render("signup.html",username=user,verify="",email=email, error=error)
        
  def get(self):
	self.render_front()
	
  def post(self):
    user=self.request.get("username")
    email=self.request.get("email")
    password=self.request.get("password")
    verify=self.request.get("verify")
    
    user_in_db=db.GqlQuery("SELECT * FROM User WHERE username=:1 limit 1", user)
    
    u = user_in_db.get()
    
    if u:
      u = u.username
    
    if u == user:      
      error="user jah existe!"
      self.render_front(user,email,error)
    else:
      if password != verify:
	error="password != verify"
	self.render_front(user,email,error)
      else:    
	u=User(username=user,password=password)
	u.put() #Stores data in database
	self.response.headers['Content-Type'] = 'text/plain'
	self.response.headers.add_header('Set-Cookie','name=%s;Path=%s' % (str(user), '/'))
	self.redirect("/")

    
class Login(Handler):
  def render_front(self,user="",email="", error=""):        
        self.render("login.html",username=user, email=email, error="")
        
  def get(self):
    user=self.request.get('username')
    email=self.request.get('email')
    self.render_front(user,email)
    
  def post(self):
    
    user = self.request.get('username')
    password = self.request.get('password')
    
    user_in_db=db.GqlQuery("SELECT * FROM User WHERE username=:1 limit 1", user)
    u = user_in_db.get()
    
    if u:
      if u.password == password:
	self.response.headers['Content-Type'] = 'text/plain'
	self.response.headers.add_header('Set-Cookie','name=%s;Path=%s' % (str(user), '/'))
	self.redirect('/blog')
    else:
      self.render_front(user,password,'erro! user or pass wrong')

class Logout(Handler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.headers.add_header('Set-Cookie','name=%s; Path=%s' % ('', '/'))
    self.redirect('/blog/signup')

        
class WikiPage(Handler):
  def get(self,slug):
    contents=db.GqlQuery("SELECT * FROM Page WHERE name=:1 ORDER BY created DESC", slug)    
    page = contents.get()   
    
    
    if page:
      self.render('view_wiki.html', p = page)
    else:
      self.redirect('/_edit'+slug)

class EditPage(Handler):
  def get(self,slug):
    contents=db.GqlQuery("SELECT * FROM Page WHERE name=:1 ORDER BY created DESC", slug)
    self.render('edit_wiki.html', p = contents.get())
    
  def post(self,slug):    
    content = self.request.get('content')
    slug = str(slug)
    p = Page(parent = wiki_key(), name = slug, content = content)
    p.put()
    self.redirect(slug)
    
class HistoryPage(Handler):
  def get(self,slug):
    contents=db.GqlQuery("SELECT * FROM Page WHERE name=:1 ORDER BY created DESC", slug)
    p_info = contents.get()
    
    self.render('history_wiki.html', contents=contents, p = p_info)
    

  
PAGE_RE = r'(/(?:[a-zA-Z0-9_-]+/?)*)'
app = webapp2.WSGIApplication([
			('/signup', SignUp),
			('/login', Login),
			('/logout', Logout),
			('/_edit' + PAGE_RE, EditPage),
			('/_history' + PAGE_RE, HistoryPage),
			(PAGE_RE, WikiPage),
			
			],
                              debug=True)
