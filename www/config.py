#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import config_default

# 实现了x.y的dict
class Dict(dict):
	
	def __init__(self, names=(), values=(), **kw):
		super(Dict, self).__init__(**kw)
		# zip()接受一系列可迭代的对象作为参数, 将对应的元素打包成一个个tuple, 然后返回由这些tuples组成的list
		# 可以用来做转置矩阵
		for k, v in zip(names, values):
			self[k] = v

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AtrributeError(r"'Dict' object has no attribute '%s'" % key)

	def __setattr__(self, key, value):
		self[key] = value

def merge(defaults, override):
	r = {}
	for k, v in defaults.items():
		if k in override:
			if isinstance(v, dict):
				# 迭代
				r[k] = merge(v, override[k])
			else:
				r[k] = override[k]
		else:
			r[k] = v
	return r

def toDict(d):
	D = Dict()
	for k, v in d.items():
		D[k] = toDict(v) if isinstance(v, dict) else v
	return D

configs = config_default.configs
try:
	import config_override
	configs = merge(configs, config_override.configs)
except ImportError:
	pass

configs = toDict(configs)