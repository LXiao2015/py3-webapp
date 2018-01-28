#!/usr/bin/env python3
#-*- coding: utf-8 -*-

'''
JSON API defination
'''
import json, logging, inspect, functools

# Base APIError, 包含error(必需), data和message
class APIError(Exception):
	
	def __init__(self, error, data='', message=''):
		super(APIError, self).__init__(message)
		self.error = error
		self.data = data
		self.message = message

# 输入值有错或无效, data指定输入表单的错误字段。
class APIValueError(APIError):

	def __init__(self, field, message=''):
		super(APIValueError, self).__init__('value:invalid', field, message)

# 资源未找到, data指定资源名称。
class APIResourceNotFoundError(APIError):

	def __init__(self, field, message=''):
		super(APIResourceNotFoundError, self).__init__('vallue:notfound', field, message)

# API没有权限。
class APIPermissionError(APIError):

	def __init__(self, message=''):
		super(APIPermissionError, self).__init__('permission:forbidden', 'permission', message)
		self.arg = arg

class Page(object):

	'''
	>>> p1 = Page(100, 1)
	>>> p1.page_count
	10
	>>> p1.offset
	0
	>> p1.limit
	10
	>>> p2 = Page(90, 9, 10)
	>>> p2.page_count
	9
	>>> p2.offset
	80
	>> p2.limit
	10
	>>> p3 = Page(91, 10, 10)
	>>> p3.page_count
	10
	>>> p3.offset
	90
	>> p3.limit
	10
	'''
	# 条目总, 跳转页码, 每页容量
	def __init__(self, item_count, page_index=1, page_size=5):
		self.item_count = item_count
		self.page_size = page_size
		# 最多能显示的页数
		self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)
		# 超出页码范围
		if (item_count == 0) or (page_index > self.page_count):
			self.offset = 0
			self.limit = 0
			self.page_index = 1
		else:
			self.page_index = page_index
			# 偏移的条目数
			self.offset = self.page_size * (page_index - 1)
			self.limit = self.page_size
		self.has_next = self.page_index < self.page_count
		self.has_previous = self.page_index > 1

	def __str__(self):
		return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)

	__repr__ = __str__

if __name__ == '__main__':
	# doctest模块搜索类似于交互式Python会话的文本段然后执行来验证是否如所示的那样
	import doctest
	doctest.testmod()
