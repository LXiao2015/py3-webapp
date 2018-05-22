#!/usr/bin/env python3
# -*- coding: utf-8 -*-

' URL handlers '
import re, time, json, logging, hashlib, base64, asyncio
import markdown2
from aiohttp import web
from coroweb import get, post
from apis import Page, APIError, APIValueError, APIResourceNotFoundError
from models import User, Comment, Blog, next_id
from config import configs

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

# +表示一或多次, {m,n}表示至少m次至多n次(因为可能是.cn或.com)
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

def user2cookie(user, max_age):
	' Generate cookie str by user. '
	expires = str(int(time.time() + max_age))
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
	# "用户id"+"过期时间"+SHA1("用户id"+"用户密码"+"过期时间"+"SecretKey")
	L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)

async def cookie2user(cookie_str):
	' Parse cookie and load user if cookie is valid. '
	if not cookie_str:
		return None
	try:
		L = cookie_str.split('-')
		if len(L) != 3:
			return None
		uid, expires, sha1 = L
		if int(expires) < time.time():
			return None
		user = await User.find(uid)
		if user is None:
			return None
		s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('Invalid sha1.')
			return None
		user.passwd = '******'
		return user
	except Exception as e:
		logging.exception(e)
		return None

def text2html(text):
	# 先将text去除空行，再写成html格式
	lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
	return ''.join(lines)

def check_admin(request):
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError()

def get_page_index(page_str):
	p = 1
	try:
		p = int(page_str)
	except ValueError as e:
		pass
	if p < 1:
		p = 1
	return p

# 后端API：
# 获取日志：GET /api/blogs
# 创建日志：POST /api/blogs
# 修改日志：POST /api/blogs/:blog_id
# 删除日志：POST /api/blogs/:blog_id/delete
# 获取评论：GET /api/comments
# 创建评论：POST /api/blogs/:blog_id/comments
# 删除评论：POST /api/comments/:comment_id/delete
# 获取用户：GET /api/users
# 创建新用户：POST /api/users

@get('/api/blogs')
async def api_blogs(request, *, page='1'):
	page_index = get_page_index(page)
	# select count(id)计算not null值个数
	if request.__user__ is None or not request.__user__.admin:
		num = await Blog.findNumber('count(id)', where='private is null or private is false')
		p = Page(num, page_index)
		if num == 0:
			return dict(page=p, blogs=())
		# LIMIT 5,10; 返回第6-15行数据
		blogs = await Blog.findAll(orderBy='created_at desc', where='private is null or private is false', limit=(p.offset, p.limit))
		return dict(page=p, blogs=blogs)

	else:
		num = await Blog.findNumber('count(id)')
		p = Page(num, page_index)
		if num == 0:
			return dict(page=p, blogs=())
		# LIMIT 5,10; 返回第6-15行数据
		blogs = await Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
		return dict(page=p, blogs=blogs)

@get('/api/blogs/{id}')
async def api_get_blog(*, id):
	blog = await Blog.find(id)
	# 返回到manage_blog_edit.html中, 当需要编辑旧博客时
	return blog

@post('/api/blogs')
async def api_create_blog(request, *, name, summary, content, private):
	check_admin(request)	# 只有管理员才可以发布博客
	if not name or not name.strip():
		raise APIValueError('name', 'name cannot be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary cannot be empty.')
	if not content or not content.strip():
		raise APIValueError('content', 'content cannot be empty.')
	blog = Blog(
		private=private,
		user_id=request.__user__.id, 	# app.py中把cookie2user获取到的用户赋给了request.__user__
		user_name=request.__user__.name, 
		user_image=request.__user__.image, 
		name=name.strip(), 
		summary=summary.strip(), 
		content=content.strip()
	)
	await blog.save()
	return blog

@post('/api/blogs/{id}')
async def api_update_blog(id, request, *, name, summary, content, private):
	# 需要传入request来检查是否为管理员
	check_admin(request)
	blog = await Blog.find(id)
	# 对于用户输入要记得检查
	if not name or not name.strip():
		raise APIValueError('name', 'name cannot be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary', 'summary cannot be empty.')
	if not content or not content.strip():
		raise APIValueError('content', 'content cannot be empty.')
	blog.name = name.strip()
	blog.summary = summary.strip()
	blog.content = content.strip()
	blog.private = private
	await blog.update()
	return blog
	
@post('/api/blogs/{id}/secret')
async def api_set_private(id, request):
	check_admin(request)
	blog = await Blog.find(id)
	if blog.private == 1:
		blog.private = 0
	else:
		blog.private = 1
	await blog.update()
	return blog.private

@post('/api/blogs/{id}/delete')
async def api_delete_blog(id, request):
	check_admin(request)
	blog = await Blog.find(id)
	await blog.remove()
	return dict(id=id)    # 谁来处理?

@get('/api/comments')
async def api_comments(*, page='1'):
	page_index = get_page_index(page)
	num = await Comment.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, comments=())
	comments = await Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	return dict(page=p, comments=comments)

@post('/api/blogs/{id}/comments')    # 参数顺序?
async def api_create_comment(id, request, *, content):
	user = request.__user__
	# 永远记得要对用户进行检查
	if user is None:
		raise APIPermissionError('Please signin first.')
	if not content or not content.strip():
		raise APIValueError('content', 'content cannot be empty.')
	# 评论id和created_at不需要指定, 可以自动生成
	blog = await Blog.find(id)
	if blog is None:
		raise APIResourceNotFoundError('Blog')
	comment = Comment(
		blog_id = blog.id,
		user_id = user.id,
		user_name = user.name,
		user_image = user.image,
		content = content.strip()
	)
	await comment.save()
	return comment

@post('/api/comments/{id}/delete')
async def api_delete_comment(id, request):
	check_admin(request)
	comment = await Comment.find(id)
	if comment is None:
		raise APIResourceNotFoundError('Comment')
	await comment.remove()
	return dict(id=id)

@get('/api/users')
async def api_get_users(*, page='1'):
	page_index = get_page_index(page)
	num = await User.findNumber('count(id)')
	p = Page(num, page_index)
	if num == 0:
		return dict(page=p, users=())
	users = await User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	for u in users:
		u.password = '******'
	return dict(page=p, users=users)

@post('/api/users')
async def api_register_user(*, email, name, passwd):
	# 用户名为空或全为空格
	if not name or not name.strip():	# 没有用户名的字符限制?
		raise APIValueError('name')
	if not email or not _RE_EMAIL.match(email):
		raise APIValueError('email')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd')
	users = await User.findAll('email=?', [email])
	if len(users) > 0:
		raise APIError('register:failed', 'email', 'Email is already in use.')
	uid = next_id()
	sha1_passwd = '%s:%s' % (uid, passwd)
	encrypt_passwd = hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest()
	# image使用Gravatar全球通用头像
	image = 'http://www.gravatar.com/avatar/%s?d=mm&s=120'
	user = User(id=uid,name=name.strip(),email=email,passwd=encrypt_passwd,image=image % hashlib.md5(email.encode('utf-8')).hexdigest())
	await user.save()
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

@post('/api/authenticate')    # 做什么用?
async def authenticate(*, email, passwd):
	if not email:
		raise APIValueError('email', 'Invalid email.')
	if not passwd:
		raise APIValueError('passwd', 'Invalid password.')
	users = await User.findAll('email=?', [email])
	if len(users) == 0:
		raise APIValueError('email', 'Email not exist.')
	user = users[0]
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd', 'Invalid password.')
	r = web.Response()
	# set_cookie(name, value, max_age, httponly(设为True在浏览器的document对象中就看不到cookie))
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd = '******'
	r.content_type = 'application/json'
	# json.dumps(obj, ensure_asci), 把python对象转换成json格式的str
	# 如果ensure_ascii为false, 则结果可能包含非ASCII字符, 并且返回值可能是一个unicode实例
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r

# 用户浏览页面：
# 首页：GET /
# 注册页：GET /register
# 登录页：GET /signin
# 注销页：GET /signout
# 日志详情页：GET /blog/:blog_id    冒号?

# 参数aiohttp.web.request实例，包含了所有浏览器发送过来的HTTP协议里面的信息
@get('/')
async def index(request, *, page='1'):
	return {
		'__template__': 'blogs.html',
		'page_index': get_page_index(page), 
		'__user__': request.__user__
	}

@get('/register')
def register():
	return {'__template__': 'register.html'}

@get('/signin')
def signin():
	return {'__template__': 'signin.html'}

@get('/signout')
def signout(request):
	referer = request.headers.get('Referer')
	# 状态码302
	r = web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME, '-delete-', max_age=0, httponly=True)
	logging.info('User signed out.')
	return r

@get('/blog/{id}')
async def get_blog(id):
	blog = await Blog.find(id)    # 根据id查询到blog对象
	comments = await Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
	for c in comments:
		c.html_content = text2html(c.content)
	blog.html_content = markdown2.markdown(blog.content)
	return {
		'__template__': 'blog.html',
		'blog': blog,
		'comments': comments
	}

# 管理页面：
# 评论列表页：GET /manage/comments
# 日志列表页：GET /manage/blogs
# 创建日志页：GET /manage/blogs/create
# 修改日志页：GET /manage/blogs/
# 用户列表页：GET /manage/users

@get('/manage/')    # 首页下面的Manage点击跳转到博客列表
def manage():
    return 'redirect:/manage/blogs'

@get('/manage/comments')
def manage_comments(*, page='1'):
	return {
		'__template__': 'manage_comments.html',
		'page_index': get_page_index(page)
	}

@get('/manage/blogs')    # 这几个对bolg操作的区别?
def manage_blogs(*, page='1'):
	return {
		'__template__': 'manage_blogs.html',
		'page_index': get_page_index(page)
	}

@get('/manage/blogs/create')
def manage_create_blogs():
	return {
		'__template__': 'manage_blog_edit.html',
		'id': '',
		'action': '/api/blogs'
	}

@get('/manage/blogs/edit')
def manage_edit_blog(*, id):
	return {
		# 可以直接使用edit的模板
		'__template__': 'manage_blog_edit.html',
		'id': id,
		'action': '/api/blogs/%s' % id
	}

@get('/manage/users')
def manage_users(*, page='1'):
	return {
		'__template__': 'manage_users.html',
		'page_index': get_page_index(page)
	}
