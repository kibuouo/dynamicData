CREATE TABLE `collection_runs` (
	`id` text PRIMARY KEY NOT NULL,
	`fetched_at` text NOT NULL,
	`source` text NOT NULL,
	`video_count` integer NOT NULL,
	`saved_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `video_online_snapshots` (
	`bvid` text NOT NULL,
	`cid` integer,
	`aid` integer,
	`抓取时间` text NOT NULL,
	`在线人数` integer,
	PRIMARY KEY(`bvid`, `抓取时间`),
	FOREIGN KEY (`bvid`) REFERENCES `popular_videos`(`bvid`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `ranking_video_snapshots` (
	`bvid` text NOT NULL,
	`榜单分区ID` integer NOT NULL,
	`榜单类型` text NOT NULL,
	`榜单排名` integer,
	`榜单分数` real,
	`榜单抓取时间` text NOT NULL,
	PRIMARY KEY(`bvid`, `榜单分区ID`, `榜单类型`, `榜单抓取时间`),
	FOREIGN KEY (`bvid`) REFERENCES `popular_videos`(`bvid`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE INDEX `idx_ranking_latest` ON `ranking_video_snapshots` (`榜单抓取时间`);--> statement-breakpoint
CREATE TABLE `popular_video_snapshots` (
	`bvid` text NOT NULL,
	`抓取时间` text NOT NULL,
	`播放量` integer,
	`弹幕数` integer,
	`评论数` integer,
	`点赞数` integer,
	`投币数` integer,
	`收藏数` integer,
	`综合热度` real,
	`疑似异常` integer,
	PRIMARY KEY(`bvid`, `抓取时间`),
	FOREIGN KEY (`bvid`) REFERENCES `popular_videos`(`bvid`) ON UPDATE no action ON DELETE no action
);
--> statement-breakpoint
CREATE TABLE `popular_videos` (
	`bvid` text PRIMARY KEY NOT NULL,
	`aid` integer,
	`cid` integer,
	`视频标题` text NOT NULL,
	`UP主` text,
	`分区` text,
	`pub_date` text,
	`视频链接` text,
	`封面链接` text,
	`时长` integer
);
