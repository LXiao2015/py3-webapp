if (! window.console) {
    window.console = {
        log: function() {},
        info: function() {},
        error: function () {},
        warn: function () {},
        debug: function () {}
    };
}

// patch for string.trim():

if (! String.prototype.trim) {
    String.prototype.trim = function() {
        return this.replace(/^\s+|\s+$/g, '');
    };
}

if (! Number.prototype.toDateTime) {
    var replaces = {
        'yyyy': function(dt) {
            return dt.getFullYear().toString();
        },
        'yy': function(dt) {
            return (dt.getFullYear() % 100).toString();
        },
        'MM': function(dt) {
            var m = dt.getMonth() + 1;
            return m<10 ? '0'+m: m.toString();
        },
        'M': function(dt) {
            var m = dt.getMonth() + 1;
            return m.toString();
        },
        'dd': function(dt) {
            var d = dt.getDate();
            return d<10? '0'+d: d.toString();
        },
        'd': function(dt) {
            var d = dt.getDate();
            return d.toString();
        },
        'hh': function(dt) {
            var h = dt.getHours();
            return h<10? '0'+h: h.toString();
        },
        'h': function(dt) {
            return dt.getHours().toString();
        },
        'mm': function(dt) {
            var m = dt.getMinutes();
            return m<10? '0'+m: m.toString();
        },
        'm': function(dt) {
            return dt.getMinutes().toString();
        },
        'ss': function(dt) {
            var s = dt.getSeconds();
            return s<10? '0'+s: s.toString();
        },
        's': function(dt) {
            return dt.getSeconds().toString();
        },
        'a': function(dt) {
            var h = dt.getHours();
            return h<12? 'AM': 'PM';
        }
    };
    var token = /([a-zA-Z]+)/;
    Number.prototype.toDateTime = function(format) {
        var fmt = format || 'yyyy-MM-dd hh:mm:ss'
        var dt = new Date(this * 1000);
        var arr = fmt.split(token);
        for (var i=0; i<arr.length; i++) {
            var s = arr[i];
            if (s && s in replaces) {
                arr[i] = replaces[s](dt);
            }
        }
        return arr.join('');
    };
}

function encodeHtml(str) {
	return String(str)
		// 把前者替换为后者
		.replace(/&/g, '&amp;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

// 将查询字符串解析为对象
function parseQueryString() {
	var
		// location.search获取从问号开始的URL(即查询部分)
		q = location.search,
		r = {},
		i, pos, s, qs;
	// charAt()方法返回指定位置的字符
	if (q && q.charAt(0)==='?') {
		qs = q.substring(1).split('&');
		for (i=0; i<qs.length; i++) {
			s = qs[i];
			pos = s.indexOf('=');
			if (pos <= 0) {
				continue;
			}
			r[s.substring(0, pos)] = decodeURIComponent(s.substring(pos+1)).replace(/\+/g, ' ');    // 正则表达式是不是错了?
		}
	}
	return r;
}

function gotoPage(i) {
	var r = parseQueryString();
	r.page = i;
	// jQuery.param()序列化一个key/value对象, 返回如width=1680&height=1050
	location.assign('?'+$.param(r));
}

function refresh() {
	var
		t = new Date().getTime(),
		url = location.pathname;
	if (location.search) {
		url = url + location.search + '&t=' + t;
	}
	else {
		url = url + '?t=' + t;
	}
	location.assign(url);
}

// 根据发帖时间和当前时间决定显示的时间格式
function toSmartDate(timestamp) {
	if (typeof(timestamp)==='string') {
		timestamp = parseInt(timestamp);
	}
	if (isNaN(timestamp)) {
		return '';
	}
	var
		today = new Date(g_time),    //g_time?
		now = today.getTime(),
		s = '1分钟前',
		t = now - timestamp;
	// 1周前
	if (t > 604800000) {
		var that = new Date(timestamp);
		var
			y = that.getFullYear(),
			m = that.getMonth() + 1,
			d = that.getDate(),
			hh = that.getHours(),
			mm = that.getMinutes();
		s = y===today.getFullYear()? '': y+'年';
		s = s + m + '月' + d + '日' + hh + ':' +(mm<10? '0': '') + mm;
	}
	// 1~6天
	else if (t >= 86400000) {
		s = Math.floor(t / 86400000) + '天前';
	}
	// 1~23小时
	else if (t >= 3600000) {
		s = Math.floor(t / 3600000) + '小时前';
	}
	else if (t >= 60000) {
		s = Math.floor(t / 60000) + '分钟前';
	}
	return s;
}

// $(function() {});是$(document).ready(function(){ })的简写
// 里面的代码是在页面元素都加载完才执行的
$(function() {
	$('.x-smartdate').each(function() {
		// $(this)是一个jQuery对象, text()设置元素的文本内容
		// attr()函数用于设置或返回当前jQuery对象所匹配的元素节点的属性值
		$(this).removeClass('x-smartdate').text(toSmartDate($(this).attr('date')));
	});
});

// 还没看懂...
function Template(tpl) {
	var
		fn,
		match,
		// 替换字符
		code = ['var r=[];\nvar _html = function (str) { return str.replace(/&/g, \'&amp;\').replace(/"/g, \'&quot;\').replace(/\'/g, \'&#39;\').replace(/</g, \'&lt;\').replace(/>/g, \'&gt;\'); };'],
		re = /\{\s*([a-zA-Z\.\_0-9()]+)(\s*\|\s*safe)?\s*\}/m,    // 两个捕获组, 这是什么字符串?
		// 定义了一个addLine函数, 接受的参数是text
		addLine = function (text) {
			code.push('r.push(\''+text.replace(/\'/g, '\\\'').replace(/\n/g, '\\n').replace(/\r/g, '\\r')+'\');');
		};
	// exec()方法用于检索字符串中的正则表达式的匹配, 返回一个数组
	// 如["abc", index: 1, input: "2abcdkfabco98787abc9"]
	while (match = re.exec(tpl)) {
		if (match.index > 0) {
			addLine(tpl.slice(0, match.index));
		}
		// 第二组的匹配结果
		if (match[2]) {
			code.push('r.push(String(this.'+match[1]+'));');
		}
		else {
			code.push('r.push(_html(String(this.'+match[1]+')));');
		}
		tpl = tpl.substring(match.index+match[0].length);
	}
	addLine(tpl);
	code.push('return r.join(\'\');');
	fn = new Function(code.join('\n'));
	this.render = function (model) {
		return fn.apply(model);    //对model?
	};
}

// 扩展jQuery.form
$(function () {
	console.log('Extends $form...');
	// jQuery.fn.extend(object)为jQuery类添加成员函数(插件)
	$.fn.extend({
		// 大多数的异步方法都接受一个callback函数, 该函数接受一个Error对象传入作为第一个参数
		// 如果第一个参数不是null而是一个Error实例, 则说明发生了错误, 应该进行处理
		showFormError: function (err) {
			// 返回this.each便于继续链式操作
			return this.each(function () {
				var
					$form = $(this),
					// find()方法获得当前元素集合中每个元素的后代, 通过选择器、jQuery对象或元素来筛选
					// uk-alert-danger是红色提示框
					$alert = $form && $form.find('.uk-alert-danger'),
					fieldName = err && err.data;
				// is()根据选择器、元素或jQuery对象来检测匹配元素集合, 如果这些元素中至少有一个元素匹配给定的参数, 则返回true
				if (! $form.is('form')) {
					console.error('Cannot call showFormError() on non-form object.');
					return;
				}
				$form.find('input').removeClass('uk-form-danger');
				$form.find('select').removeClass('uk-form-danger');
				$form.find('textarea').removeClass('uk-form-danger');
				if ($alert.length === 0) {
					console.warn('Cannot find .uk-alert-danger element.');
					return;
				}
				if (err) {
					$alert.text(err.message? err.message: (err.error? err.error: err)).removeClass('uk-hidden').show();
					// offset()方法获得匹配元素在当前窗口的偏移, 有top和left两个属性
					// scrollTop()方法返回匹配元素的滚动条的垂直位置
					if (($alert.offset().top - 60) < $(window).scrollTop()) {
						$('html,body').animate({ scrollTop: $alert.offset().top - 60});
					}
					if (fieldName) {
						// jQuery按属性查找, 注册页里没有name属性?
						$form.find('[name='+fieldName+']').addClass('uk-form-danger');
					}
				}
				else {
					$alert.addClass('uk-hidden').hide();
					$form.find('.uk-form-danger').removeClass('uk-form-danger');
				}
			});
		},
		// 用在下面postJSON, 发送数据时
		showFormLoading: function (isLoading) {
			return this.each(function () {
				var
					$form = $(this),
					$submit = $form && $form.find('button[type=submit]'),
					$buttons = $form && $form.find('button'),
					$i = $submit && $submit.find('i'), 
                    iconClass = $i && $i.attr('class');
				if (! $form.is('form')) {
					console.error('Cannot call showFormLoading() on non-form object.');
					return;
				}
				if (!iconClass || iconClass.indexOf('uk-icon') < 0) {
					console.warn('Icon <i class="uk-icon-*"> not found.');    //改了一下
					return;
				}
				if (isLoading) {
					// attr('disabled','disabled')将页面中某个元素置为不可编辑或触发状态
					$buttons.attr('disabled', 'disabled');
					$i && $i.addClass('uk-icon-spinner').addClass('uk-icon-spin');
				}
				else {
					$buttons.removeAttr('disabled');
					$i && $i.removeClass('uk-icon-spinner').removeClass('uk-icon-spin');
				}
			});
		},
		postJSON: function (url, data, callback) {
			if (arguments.length===2) {
				callback = data;
				data = {};
			}
			return this.each(function () {
				var $form = $(this);
				$form.showFormError();    //这里的作用?
				$form.showFormLoading(true);
				_httpJSON('POST', url, data, function (err, r) {
					if (err) {
						$form.showFormError(err);
						$form.showFormLoading(false);
					}
					callback && callback(err, r);
				});
			});
		}
	});
});

// ajax提交表单
function _httpJSON(method, url, data, callback) {
	var opt = {
		type: method,
		dataType: 'json'
	};
	if (method==='GET') {
		opt.url = url + '?' + data;
	}
	if (method==='POST') {
		opt.url = url;
		// JSON.stringify()用于将JavaScript值转换为JSON字符串
		opt.data = JSON.stringify(data || {});
		opt.contentType = 'application/json';
	}
	// ajax()方法通过HTTP请求加载远程数据
	// jQuery.ajax返回的是jqXHR对象, 它是浏览器原生XMLHttpRequest对象的一个超集
	// 并实现了Promise接口, 使它拥有了Promise的所有属性、方法和行为
	// jqXHR.done(function(data,textStatus,jqXHR){}), 一种可供选择的请求成功时调用的回调选项构造函数
	$.ajax(opt).done(function (r) {
		if (r && r.error) {
			return callback(r);
		}
		return callback(null, r);
	// jqXHR.fail(function(jqXHR,textStatus,errorThrown){}), 一种可供选择的请求失败时调用的回调选项构造函数
	}).fail(function (jqXHR, textStatus) {
		return callback({'error': 'http_bad_response', 'data': ''+jqXHR.status, 'message': '网络好像出问题了(HTTP'+jqXHR.status+')'});
	});
}

function getJSON(url, data, callback) {
	if (arguments.length===2) {
		callback = data;
		data = {};
	}
	if (typeof (data)==='object') {
		var arr = [];
		$.each(data, function (k, v) {
			// encodeURIComponent()函数可把字符串作为URI组件进行编码
			// 该方法不会对ASCII字母和数字进行编码, 也不会对这些ASCII标点符号进行编码：- _ . ! ~ * ' ( )
			// 其他字符(如;/?:@&=+$,#这些用于分隔URI组件的标点符号), 都是由一个或多个十六进制的转义序列替换的
			arr.push(k+'='+encodeURIComponent(v));
		});
		data = arr.join('&');
	}
	 _httpJSON('GET', url, data, callback);
}

function postJSON(url, data, callback) {
	if (arguments.length===2) {
		callback = data;
		data = {};
	}
	_httpJSON('POST', url, data, callback);
}

if (typeof(Vue)!=='undefined') {    // Vue在哪里出现?
	// 全局过滤器Vue.filter(名字,function (val))
	Vue.filter('datetime', function (value) {
		var d = value;
		if (typeof(value)==='number') {
			d = new Date(value);
		}
		return d.getFullYear()+'-'+(d.getMonth()+1)+'-'+d.getDate()+' '+d.getHours()+':'+d.getMinutes();
	});
	// Vue.component(在html文件里使用的tag, template)
	Vue.component('pagination', {
		template: '<ul class="uk-pagination">' +
			// v-if条件渲染指令, 根据其后表达式的bool值判断是否渲染该元素
			'<li v-if"! has_previous" class="uk-disabled"><span><i class="uk-icon-angle-double-left"></i></span></li>' +
			// 定义on—click函数, 动作是gotoPage(page_index-1)
			// 用#定义锚点, 浏览器读取这个URL后, 会自动将id=0的位置滚动至可视区域
			'<li v-if="has_previous"><a v-attr="onclick:\'gotoPage(\'+(page_index-1)+\')\'" href="#0"><i class="uk-icon-angle-double-left"></i></a></li>' +
			// v-text操作元素中的纯文本
			'<li class="uk-active"><span v-text="page_index"></span></li>' +
			'<li v-if="! has_next" class="uk-disabled"><span><i class="uk-icon-angle-double-right"></i></span></li>' +
			'<li v-if="has_next"><a v-attr="onclick:\'gotoPage(\'+(page_index+1)+\')\'" href="#0"><i class="uk-icon-angle-double-right"></i></a></li>' +
		'</ul>'
	});
}

// 重定向
function redirect(url) {
	var
		hash_pos = url.indexOf('#'),
		query_pos = url.indexOf('?'),
		hash = '';
	if (hash_pos >= 0) {
		hash = url.substring(hash_pos);
		url = url.substring(0, hash_pos);
	}
	url = url + (query_pos>=0? '&': '?') + 't=' + new Date().getTime() + hash;
	console.log('Redirect to: ' + url);
	location.assign(url);
}

function _bindSubmit($form) {
	// 将函数绑定到submit事件
	$form.submit(function (event) {
		event.preventDefault();
		showFormError($form, null);
		var
			fn_error = $form.attr('fn-error'),    // 三个属性在哪?
			fn_success = $form.attr('fn-success'),
			fn_data = $form.attr('fn-data'),
			// serialize()方法通过序列化表单值, 创建URL编码文本字符串, 如a=1&b=2&c=3
			data = fn_data? window[fn_data]($form): $form.serialize();    // window[fn_data]($form)什么意思?
		var
			$submit = $form.find('button[type=submit]'),
			$i = $submit.find('i'),
			iconClass = $i.attr('class');
		if (!iconClass || iconClass.indexOf('uk-icon') < 0) {
			$i = undefined;
		}
		$submit.attr('disabled', 'disabled');
		$i && $i.addClass('uk-icon-spinner').addClass('uk-icon-spin');
		postJSON($form.attr('action-url'), data, function (err, result) {
			$i && $i.removeClass('uk-icon-spinner').removeClass('uk-icon-spin');
			if (err) {
				console.log('postJSON failed: ' + JSON.stringify(err));
				$submit.removeAttr('disabled');
				fn_error? fn_error(): showFormError($form, err);    // fn_error()?
			}
			else {
				var r=fn_success? window[fn_success](result): false;    // window[fn_success](result)什么意思?
				if (r===false) {
					$submit.removeAttr('disabled');
				}
			}
		});
	});
	$form.find('button[type=submit]').removeAttr('disabled');
}

$(function () {
	$('form').each(function () {
		var $form = $(this);
		if ($form.attr('action-url')) {
			_bindSubmit($form);
		}
	});
});

$(function() {
	if (location.pathname==='/' || location.pathname.indexOf('/blog')===0) {
		$('li[data-url=blogs]').addClass('uk-active');
	}
});

function _display_error($obj, err) {
	// 选择器选取每个当前是可见的元素, 除以下几种情况之外的元素即是可见元素:
	// 设置为 display:none
	// type="hidden" 的表单元素
	// Width 和 height 设置为 0
	// 隐藏的父元素(同时隐藏所有子元素)
	if ($obj.is(':visible')) {
		$obj.hide();
	}
	var msg = err.message || String(err);
	var L = ['<div class="uk-alert uk-alert-danger">'];
	L.push('<p>Error: ');
	L.push(msg);
	L.push('</p><p>Code: ');
	L.push(err.error || '500');
	L.push('</p></div>');
	// slideDown()以滑动方式显示隐藏的<p>元素
	$obj.html(L.join('')).slideDown();
}

function error(err) {
	_display_error($('#error'), err);
}

function fatal(err) {
	_display_error($('#loading'), err);
}
