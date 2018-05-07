# -*- coding: utf-8 -*-
import asyncio, logging
import aiomysql

# 创建占位符?
def create_args_string(num):
	return ', '.join('?' * num)

# 打印SQL语句
def log(sql, args=()):
    logging.info('SQL: %s' % sql)

# sql语句, sql参数和最大返回条数
async def select(sql, args, size=None):
	log(sql, args)
	global __pool

	# yield from会在内部自动捕获StopIteration异常, 还会把value属性的值变成yield from表达式的值
	# with (yield from __pool) as conn:
	async with __pool.get() as conn:

		# 通过aiomysql.DictCursor获取到的cursor在返回结果时会返回一个dict格式
		cur = await conn.cursor(aiomysql.DictCursor)
		# SQL语句的占位符是?, MySQL的占位符是%s, 因此需要替换
		# yield from cur.execute(sql.replace('?', '%s'), args or ())
		await cur.execute(sql.replace('?', '%s'), args or ())
		if size:
			rs = await cur.fetchmany(size)
		else:
			rs = await cur.fetchall()
		await cur.close()
		logging.info('Rows returned: %s' % len(rs))
		return rs

# INSERT, UPDATE和DELETE共用一个处理函数, 因为需要的参数一样
async def execute(sql, args, autocommit=True):
	log(sql)
	async with __pool.get() as conn:
		if not autocommit:    # 作用?
			await conn.begin()
		try:
			cur = await conn.cursor()
			await cur.execute(sql.replace('?', '%s'), args)
			affected = cur.rowcount
			await cur.close()
			if not autocommit:
				await conn.commit()
		except BaseException as e:
			if not autocommit:
				await conn.rollback()
			raise
		# 释放连接池，否则会报错"RuntimeError: Event loop is closed"
		finally:
			conn.close()
		return affected

class Field(object):

	# 字段名, 字段类型, 是否为主键, 默认值
	def __init__(self, name, column_type, primary_key, default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default

	# 打印实例
	def __str__(self):
		return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

# 映射varchar
class StringField(Field):

	def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
		super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):

	def __init__(self, name=None, primary_key=False, default=False, ddl='boolean'):
		super().__init__(name, ddl, primary_key, default)

class IntegerField(Field):

	def __init__(self, name=None, primary_key=False, default=0, ddl='bigint'):
		super().__init__(name, ddl, primary_key, default)

class FloatField(Field):

	def __init__(self, name=None, primary_key=False, default=0.0, ddl='real'):
		super().__init__(name, ddl, primary_key, default)

# 长文本型
class TextField(Field):

	def __init__(self, name=None, primary_key=False, default=None, ddl='text'):
		super().__init__(name, ddl, primary_key, default)

# metaclass是类的模板, 所以必须从type类型派生
class ModelMetaclass(type):

	# 当前准备创建的类的对象, 类的名字, 类继承的父类集合, 类的方法/属性集合
	def __new__(cls, name, bases, attrs):
		# 排除掉对Model类的修改
		if name == 'Model':
			return type.__new__(cls, name, bases, attrs)
		tableName = attrs.get('__table__', None) or name
		logging.info('Found model: %s (table: %s)' % (name, tableName))
		
		# 在当前类中查找定义的类的所有属性, 如果找到一个Field属性, 就把它保存到一个__mappings__的dict中
		# 同时从类属性中删除该Field属性, 否则容易造成运行时错误(实例的属性会遮盖类的同名属性)
		mappings = dict()
		fields = []
		primaryKey = None
		for k, v in attrs.items():
			if isinstance(v, Field):
				logging.info('  Found mapping: %s ==> %s' % (k, v))
				mappings[k] = v
				if v.primary_key:
					if primaryKey:
						raise StandardError('Duplicate primary key for field: %s' % k)
					primaryKey = k
				else:
					fields.append(k)
		if not primaryKey:
			raise StandardError('Primary key not found.')
		for k in mappings.keys():
			attrs.pop(k)

		# map(func, iter)返回一个新的iterable, 保存除主键外的属性名为以反单引号括起来的形式, 再用list()转化为列表
		escaped_fields = list(map(lambda f: '`%s`' % f, fields))

		attrs['__mappings__'] = mappings    # 保存属性和列的映射关系
		attrs['__table__'] = tableName
		attrs['__primary_key__'] = primaryKey
		attrs['__fields__'] = fields

		# 构造默认的SELECT, INSERT, UPDATE和DELETE语句
		# SELECT 列名称 FROM 表名称
		attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
		# INSERT INTO 表名称 (列1, 列2,...) VALUES (值1, 值2,....)
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields)+1))
		# UPDATE 表名称 SET 列名称=新值 WHERE 列名称=某值, mappings.get(f).name作用?
		attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
		# DELETE FROM 表名称 WHERE 列名称=值
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
		return type.__new__(cls, name, bases, attrs)

# 数据库的Model基类, 继承自dict, 使用ModelMetaclass来定制类
class Model(dict, metaclass=ModelMetaclass):

	def __init__(self, **kw):
		# super(B, self)首先找到B的父类A, 然后把类B的对象self转换为类A的对象, 然后“被转换”的类A对象调用自己的__init__函数
		super(Model, self).__init__(**kw)

    # 实现魔术方法__getattr__()和__setattr__()
    # 可以像引用普通字段那样写"类名.属性", 调用不存在的属性时可以不报错, 有返回值
	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)
	
	def __setattr__(self, key, value):
		self[key] = value

	def getValue(self, key):
		# default值None
		return getattr(self, key, None)

	def getValueOrDefault(self, key):
		value = getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				# default可以是由函数动态更新的也可以直接设为值, 所以这里选择是哪一种
				value = field.default() if callable(field.default) else field.default
				logging.debug('Using default value for %s: %s' % (key, str(value)))
				setattr(self, key, value)
		return value

	# classmethod修饰符对应的函数不需要实例化, 不需要self参数, 但第一个参数是表示自身类的cls
	# 可以来调用类的属性, 类的方法, 实例化对象等
	@classmethod
	async def findAll(cls, where=None, args=None, **kw):
		' Find object by where clause. '
		sql = [cls.__select__]
		if where:
			sql.append('where')
			sql.append(where)
		orderBy = kw.get('orderBy', None)
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
		if args == None:
			args = []
		limit = kw.get('limit', None)
		if limit is not None:
			sql.append('limit')
			# LIMIT 5; 返回前5行
			if isinstance(limit, int):
				sql.append('?')
				args.append(limit)
			# LIMIT 5,10; 返回第6-15行数据
			elif isinstance(limit, tuple):
				sql.append('?, ?')
				# extend()用于在列表末尾一次性追加另一个序列中的多个值（用新列表扩展原来的列表）
				args.extend(limit)
			else:
				raise ValueError('Invalid limit value: %s' % str(limit))
		rs = await select(' '.join(sql), args)
		return [cls(**r) for r in rs]

	@classmethod
	async def findNumber(cls, selectField, where=None, args=None):
		' Find number by select and where. '
		# SELECT COUNT(列名称) AS 返回名 FROM 表名称 WHERE 列名称=某值，返回名在此命名为_num_, 值为查询到的条数
		sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = await select(' '.join(sql), args, 1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']

	@classmethod
	async def find(cls, pk):
		' Find object by primary key. '
		# select('select `主键`,`列1`,`列2`,... from `表名称` where `%s`=?' % (cls.__primary_key__), [主键值], 返回条数)
		rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])    # 返回cls类的一个实例, 初始化的参数是rs[0]（**代表关键字参数, 类型为dict）

	async def save(self):
		args = list(map(self.getValueOrDefault, self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows = await execute(self.__insert__, args)
		if rows != 1:
			logging.warn('Failed to insert record: affected rows: %s' % rows)

	async def update(self):
		args = list(map(self.getValue, self.__fields__))
		args.append(self.getValue(self.__primary_key__))
		rows = await execute(self.__update__, args)
		if rows != 1:
			logging.warn('failed to update by primary key: affected rows: %s' % rows)

	async def remove(self):
		args = [self.getValue(self.__primary_key__)]
		rows = await execute(self.__delete__, args)
		if rows != 1:
			logging.warn('failed to remove by primary key: affected rows: %s' % rows)

async def create_pool(loop, **kw):
	logging.info('Create database connection pool...')

	#存储连接池, 每个HTTP请求都可以从中直接获取数据库连接
	global __pool
	__pool = await aiomysql.create_pool(
		host=kw.get('host', 'localhost'),
		port=kw.get('port', 3306),
		user=kw['user'],
		password=kw['password'],
		db=kw['db'],
		charset=kw.get('charset', 'utf8'),    #缺省设为utf8
		autocommit=kw.get('autocommit', True),    #缺省设为自动提交
		maxsize=kw.get('maxsize', 10),
		minsize=kw.get('minsize', 1),
		loop=loop
	)

class User(Model):
    __table__ = 'users'
    id = IntegerField(primary_key=True)
    name = StringField()
