#!/usr/bin/env python3

import os, sys, time, subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

def log(s):
	print('[Monitor] %s' % s)

class MyFileSystemEventHandler(FileSystemEventHandler):

	def __init__(self, fn):
		super(MyFileSystemEventHandler, self).__init__()
		self.restart = fn

	def on_any_event(self, event):
		if event.src_path.endswith('.py'):
			log('Python source file changed: %s' % event.src_path)
			self.restart()
		if event.src_path.endswith('.html'):
			log('HTML source file changed: %s' % event.src_path)
			self.restart()

command = ['echo', 'ok']    # 任意初始化两个字符串, 只是为了表明command一般由两段组成
process = None

def kill_process():
	global process
	if process:
		log('Kill process [%s]...' % process.pid)
		process.kill()
		process.wait()
		log('Process ended with code %s.' % process.returncode)
		process = None

def start_process():
	# global语句, 为定义在函数外的变量赋值, 或明确将要使用的变量是全局的而不是局部定义的
	global process, command
	log('Start process %s...' % ' '.join(command))
	process = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)

def restart_process():
	kill_process()
	start_process()

def start_watch(path, callback):
	# Observer类实现了监控文件变化触发对应事件的类, 然后调用关联的事件处理类来处理事件
	# 该类其实是threading.Thread的子类, 通过observer.start()使之运行在一个线程中, 不会阻塞主进程运行
	# 然后可以调用observer.stop()来停止该线程
	observer = Observer()
	# observer.schedule(event_handler,path,recursive=False)监控指定路径path
	# 该路径触发任何事件都会调用event_handler来处理, 如果path是目录, recursive=True则会递归监控该目录的所有变化
	# 当path变化时, 就会产生一个特定事件, 也就是event类的子类, 包含属性event_type,src_path,is_directory
	observer.schedule(MyFileSystemEventHandler(restart_process), path, recursive=True)
	observer.start()
	log('Watching directioy %s...' % path)
	start_process()
	try:
		while True:
			time.sleep(0.5)
	except KeyboardInterrupt:
		observer.stop()
	# 阻塞正在调用的线程，直到被调用join()方法的线程结束
	observer.join()

if __name__ == '__main__':
	argv = sys.argv[1:]    # 用法./pymonitor.py app.py
	if not argv:
		print('Usage: ./pymonitor your_script.py')
		exit(0)    # 正常退出
	if argv[0] != 'python3':
		argv.insert(0, 'python3')
	command = argv
	path = os.path.abspath('.')    # 当前目录
	start_watch(path, None)
