drop database if exists awesome;

create database awesome;
use awesome;
# 将awesome数据库下所有表的增删改查权限授予指定用户'www-data', 密码为'www-data'
grant select, insert, update, delete on awesome.* to 'www-data'@'localhost' identified by 'www-data';

create table users (
	`id` varchar(50) not null,
	`email` varchar(50) not null,
	`passwd` varchar(50) not null,
	`admin` bool not null,
	`name` varchar(50) not null,
	`image` varchar(500) not null,
	`created_at` real not null,
	# 在email列创建UNIQUE约束，约束名为idx_email
	unique key `idx_email` (`email`),
	# 为created_at字段创建索引，加快查询速度
	key `idx_created_at` (`created_at`),
	primary key (`id`)
) engine=innodb default charset=utf8;

create table blogs (
	`id` varchar(50) not null,
	`user_id` varchar(50) not null,
	`user_name` varchar(50) not null,
	`user_image` varchar(500) not null,
	`name` varchar(50) not null,
	`summary` varchar(200) not null,
	`content` mediumtext not null,
	`tag1` varchar(50) not null,
	`tag2` varchar(50) not null,
	`tag3` varchar(50) not null,
	`private` bool not null,
	`created_at` real not null,
	key `idx_created_at` (`created_at`),
	primary key (`id`)
) engine=innodb default charset=utf8;

create table bookmarks (
	`id` varchar(50) not null,
	`user_id` varchar(50) not null,
	`user_name` varchar(50) not null,
	`name` varchar(50) not null,
	`summary` varchar(200) not null,
	`url` mediumtext not null,
	`tag1` varchar(50) not null,
	`tag2` varchar(50) not null,
	`tag3` varchar(50) not null,
	`private` bool not null,
	`created_at` real not null,
	key `idx_created_at` (`created_at`),
	primary key (`id`)
) engine=innodb default charset=utf8;

create table comments (
	`id` varchar(50) not null,
	`blog_id` varchar(50) not null,
	`user_id` varchar(50) not null,
	`user_name` varchar(50) not null,
	`user_image` varchar(500) not null,
	`content` mediumtext not null,
	`created_at` real not null,
	key `idx_created_at` (`created_at`),
	primary key (`id`)
) engine=innodb default charset=utf8;

create table tags (
	`id` varchar(50) not null,
	`tag` varchar(50) not null,
	primary key (`id`)
) engine=innodb default charset=utf8;
