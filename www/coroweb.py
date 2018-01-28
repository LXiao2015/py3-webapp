# -*- coding: utf-8 -*-

import asyncio, os, inspect, logging, functools
from urllib import parse
from aiohttp import web
from apis import APIError

# 装饰器, 在函数前面写上@get的话, 将执行装饰器返回的函数
# 作用是一个函数通过@get()的装饰就附带了URL信息
# 由于decorator本身需要传入参数, 需要编写一个返回decorator的高阶函数
def get(path):
	'''
	Define decorator @get('/path')
	'''
	def decorator(func):
		# @functools.wraps(func)用来把原始函数的__name__等属性复制到decorator()函数中
		@functools.wraps(func)
		# (*args, **kw)表示wrapper()函数可以接受任意参数的调用
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'GET'
		wrapper.__route__ = path
		return wrapper
	return decorator

def post(path):
	'''
	Define decorator @post('/path')
	'''
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__ = 'POST'
		wrapper.__route__ = path
		return wrapper
	return decorator

# 运用inspect模块，创建几个函数用以获取URL处理函数与request参数之间的关系
# 收集没有默认值的命名关键字参数
def get_required_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	# 如果纯使用for..in则只能取得每一对元素的key值
	for name, param in params.items():
		# 只能用关键字KEYWORD来传参，不可以用位置传参，因为位置参数全让前面的VAR_POSITIONAL类型参数接收完了
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
			args.append(name)
		return tuple(args)

# 获取命名关键字参数
def get_named_kw_args(fn):
	args = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			args.append(name)
	return tuple(args)

# 判断有没有命名关键字参数
def has_named_kw_args(fn):
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			return True

# 判断有没有关键字参数
def has_var_kw_arg(fn):
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.VAR_KEYWORD:
			return True

# 判断是否含有名叫'request'参数，且该参数是否为最后一个参数
def has_request_arg(fn):
	sig = inspect.signature(fn)
	params = sig.parameters
	found = False
	for name, param in params.items():
		if name == 'request':
			found = True
			continue
		if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
	return found

# 正式向request参数获取URL处理函数所需的参数
class RequestHandler(object):

	# 接受app参数
	def __init__(self, app, fn):
		self._app = app
		self._func = fn
		self._has_request_arg = has_request_arg(fn)
		self._has_var_kw_arg = has_var_kw_arg(fn)
		self._has_named_kw_args = has_named_kw_args(fn)
		self._named_kw_args = get_named_kw_args(fn)
		self._required_kw_args = get_required_kw_args(fn)

	async def __call__(self, request):
		# print(self._required_kw_args)
		kw = None
		if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
			if request.method == 'POST':
				if not request.content_type:
					return web.HTTPBadRequest(text='Missing Content-Type.')
				ct = request.content_type.lower()
				if ct.startswith('application/json'):
					params = await request.json()    # .json()?
					if not isinstance(params, dict):
						return web.HTTPBadRequest(text='JSON body must be object.')
					kw = params
				# 键值对或表单
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
					params = await request.post()    # .post()?
					# 内置函数dict(**kwarg)从一个字典参数构造一个新字典
					kw = dict(**params)
				else:
					return web.HTTPBadRequest(text='Unsupported Content-Type: %s' % request.content_type)
			if request.method == 'GET':
				qs = request.query_string
				if qs:
					kw = dict()
					# urllib.parse.parse_qs(qs, keep_blank_values, strict_parsing=False)
					# 解析qs给出的查询字符串(例如'foo=bar&baz=qux'), 数据作为字典返回，保留空白字符串。
					for k, v in parse.parse_qs(qs, True).items():
						kw[k] = v[0]
		if kw is None:
			kw = dict(**request.match_info)
		else:
			if not self._has_var_kw_arg and self._named_kw_args:    # ?
				# 去掉不是命名关键字参数的参数
				copy = dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name] = kw[name]
				kw = copy
			# 检查命名关键字参数
			for k, v in request.match_info.items():    # ?
				if k in kw:
					logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
				kw[k] = v
		if self._has_request_arg:
			kw['request'] = request
		# 检查没有默认值的命名关键字参数
		if self._required_kw_args:
			for name in self._required_kw_args:
				if name not in kw:
					return web.HTTPBadRequest(text='Missing argument: %s' % name)
		logging.info('Call with arg: %s' % str(kw))
		try:
			r = await self._func(**kw)
			return r
		except APIError as e:
			return dict(error=e.error, data=e.data, message=e.message)

# 添加静态资源路径
def add_static(app):
	# os.path.abspath()返回绝对路径, os.path.dirname()返回path的目录名, os.path.join()将多个路径组合
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
	# add_static(处理的静态资源的URL路径前缀, 文件系统中包含处理的静态资源的文件夹路径)
	app.router.add_static('/static/', path)
	logging.info('add static %s => %s' % ('/static/', path))

# 注册URL处理函数
def add_route(app, fn):
	# getattr(self, key, default值)
	method = getattr(fn, '__method__', None)
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in %s.' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
	# inspect.signature(fn)将返回一个inspect.Signature类型的对象, 值为fn这个函数的所有参数
	# inspect.Signature对象的paramerters属性是一个mappingproxy(映射)类型的对象，值为一个有序字典(Orderdict)。
	# 这个字典里的key即为参数名，str类型; value是一个inspect.Parameter类型的对象，包含的一个参数的各种信息
	logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
	app.router.add_route(method, path, RequestHandler(app, fn))

def add_routes(app, module_name):
	# rfind(字符串)返回字符串最后一次出现的位置, 如果没有匹配项则返回-1
	n = module_name.rfind('.')
	if n == -1:
		# __import__(name[, globals[, locals[, fromlist[, level]]]])函数用于动态加载类和函数
		# globals()返回全局变量的字典, locals()返回当前局部变量的深拷贝(新建对象，不改变原值)
		mod = __import__(module_name, globals(), locals())
	else:
		name = module_name[n+1:]
		mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
	# dir()函数可以查看对象内所有属性及方法
	for attr in dir(mod):
		if attr.startswith('_'):
			continue
		fn = getattr(mod, attr)
		if callable(fn):
			method = getattr(fn, '__method__', None)
			path = getattr(fn, '__route__', None)
			if method and path:
				add_route(app, fn)
