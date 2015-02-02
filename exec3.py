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
class Art(db.Model):
    subject=db.StringProperty(required=True)
    content=db.TextProperty(required=True)
    created=db.DateTimeProperty(auto_now_add=True)
    last_modified=db.DateTimeProperty(auto_now = True)
    
    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

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
def blog_key(name = 'default'):
  return db.Key.from_path('arts', name)

first_date = time.time()
delta_date = time.time()

def cache_front(update=False):
  key='front'  
  contents = memcache.get(key)
  global delta_date
  global first_date
  
  if contents is None or update:
    logging.error("DB Query")
    contents=db.GqlQuery("SELECT * FROM Art ORDER BY created DESC")
    memcache.set(key, contents)
  
  t = time.time()
  delta_date = (t - first_date)
    
    
  logging.error(delta_date)
  return contents
  
def cache_post(post_id, update=False):
  
  post = memcache.get(post_id)
  key_str = str(post_id)+'_t'
  
  if post is None or update:
    logging.error("DB Query post %s" % post_id)
    key = db.Key.from_path('Art', int(post_id), parent=blog_key())
    post = db.get(key)
    memcache.set(post_id, post)    
    memcache.set(key_str, time.time()) 
    
  return (post)
  

class Home(Handler):
        
    
    def render_front(self,username="",subject="",content="",error=""):

	contents=cache_front()

        self.render("home.html",username=username,contents=contents, time=int(delta_date))

    def get(self):
        #self.write("asciichan!")
        user=self.request.cookies.get('name')        
        self.render_front(user)

class NewPost(Handler):
    def get(self):
        self.render("newpost.html")

    def post(self):
        subject = self.request.get('subject')
        content = self.request.get('content')

        if subject and content:
            p = Art(parent = blog_key(), subject = subject, content = content)
            p.put()
            self.redirect('/blog/%s' % str(p.key().id()))
        else:
            error = "subject and content, please!"
            self.render("newpost.html", subject=subject, content=content, error=error)

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
	self.redirect("/blog")

class Welcome(Handler):
  def render_front(self,user="",email="", error=""):        
        self.render("welcome.html",username=user, error=error)
        
  def get(self):
    user=self.request.cookies.get('name')
    self.render_front(user)
    
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

class PostPage(Handler):
  
    def get(self, post_id):	
        ############        
        post = cache_post(post_id)
	logging.error(post.content)        
        if not post:
            self.error(404)
            return
        
        t_0 = long(memcache.get(post_id+'_t')) or time.time()
    
	t = time.time()
  
	dt = int(t - t_0)
	
	self.render("permalink.html", post=post, time=dt)
        
        

class JSON(Handler):
  def render_json(self, post_id):    
    jstruct = []
    c = 'content'
    s = 'subject'
    self.response.headers['Content-Type'] = 'application/json'
    
    if str(post_id) == '.json':    
      contents=db.GqlQuery("SELECT * FROM Art ORDER BY created DESC")
      
      for e in contents:
	jstruct.append({c:e.content, s:e.subject})
      
    else:
      key = db.Key.from_path('Art', int(post_id), parent=blog_key())
        
      post = db.get(key)
      
      if not post:
	self.error(404)
	return
      
      jstruct.append({c:post.content, s:post.subject})
      
    self.render("json.js",json_struct=json.dumps(jstruct))
           
    
  def get(self, post_id):
    
    self.render_json(post_id)
    
class Flush(Handler):
  
  def get(self):
    global delta_date
    global first_date
    
    delta_date=time.time()
    first_date=delta_date
    
    
    memcache.delete('front')
    memcache.flush_all()
    self.redirect('/blog')
  
app = webapp2.WSGIApplication([('/blog/?', Home),
			('/blog/([0-9]+)', PostPage),
			('/blog/(.json)', JSON),
			('/blog(.json)', JSON),
			('/blog/([0-9]+).json', JSON),
			('/blog/newpost', NewPost),
			('/blog/signup', SignUp),
			('/blog/login', Login),
			('/blog/logout', Logout),
			('/blog/flush', Flush)],
                              debug=True)
