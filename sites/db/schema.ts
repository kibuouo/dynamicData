import { sqliteTable, text, integer, real, primaryKey, index } from 'drizzle-orm/sqlite-core';
export const videos = sqliteTable('popular_videos', {
  bvid: text('bvid').primaryKey(), aid: integer('aid'), cid: integer('cid'),
  title: text('视频标题').notNull(), up: text('UP主'), category: text('分区'),
  pubDate: text('pub_date'), url: text('视频链接'), cover: text('封面链接'), duration: integer('时长')
});
export const snapshots = sqliteTable('popular_video_snapshots', {
  bvid: text('bvid').notNull().references(()=>videos.bvid), fetchedAt: text('抓取时间').notNull(),
  views: integer('播放量'), danmaku: integer('弹幕数'), replies: integer('评论数'),
  likes: integer('点赞数'), coins: integer('投币数'), favorites: integer('收藏数'),
  heat: real('综合热度'), anomaly: integer('疑似异常')
}, t=>[primaryKey({columns:[t.bvid,t.fetchedAt]})]);
export const ranking = sqliteTable('ranking_video_snapshots', {
  bvid: text('bvid').notNull().references(()=>videos.bvid), rid: integer('榜单分区ID').notNull(),
  type: text('榜单类型').notNull(), rank: integer('榜单排名'), score: real('榜单分数'),
  fetchedAt: text('榜单抓取时间').notNull()
}, t=>[primaryKey({columns:[t.bvid,t.rid,t.type,t.fetchedAt]}),index('idx_ranking_latest').on(t.fetchedAt)]);
export const online = sqliteTable('video_online_snapshots', {
  bvid: text('bvid').notNull().references(()=>videos.bvid), cid: integer('cid'), aid: integer('aid'),
  fetchedAt: text('抓取时间').notNull(), count: integer('在线人数')
}, t=>[primaryKey({columns:[t.bvid,t.fetchedAt]})]);
export const imports = sqliteTable('collection_runs', {
  id: text('id').primaryKey(), fetchedAt: text('fetched_at').notNull(),
  source: text('source').notNull(), count: integer('video_count').notNull(), savedAt: text('saved_at').notNull()
});
