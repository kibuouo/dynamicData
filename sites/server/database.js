export function getDb(env){if(!env.DB)throw new Error('D1 database binding is unavailable');return env.DB;}

// The capture is stored once. Repeated calls use deterministic keys and never clear history.
export async function ensureCapture(db,capture){
 if(await db.prepare('SELECT id FROM collection_runs WHERE id = ?').bind(capture.id).first())return;
 const statements=[];
 // JSON is bound as data: one parameter per statement, even for 500 videos.
 const add=(prefix,rows,conflict)=>{
  if(!rows.length)return;
  const columns=rows[0].map((_,i)=>`json_extract(value, '$[${i}]')`).join(',');
  statements.push(db.prepare(`${prefix} SELECT ${columns} FROM json_each(?) WHERE 1 ${conflict}`).bind(JSON.stringify(rows)));
 };
 add(`INSERT INTO popular_videos (bvid,aid,cid,"视频标题","UP主","分区",pub_date,"视频链接","封面链接","时长")`,capture.videos.map(v=>[v.bvid,v.aid,v.cid,v.title,v.up,v.category,v.pubDate,v.url,v.cover,v.duration]),'ON CONFLICT(bvid) DO UPDATE SET aid=excluded.aid,cid=excluded.cid,"视频标题"=excluded."视频标题","UP主"=excluded."UP主","分区"=excluded."分区",pub_date=excluded.pub_date,"视频链接"=excluded."视频链接","封面链接"=excluded."封面链接","时长"=excluded."时长"');
 add(`INSERT INTO popular_video_snapshots (bvid,"抓取时间","播放量","弹幕数","评论数","点赞数","投币数","收藏数","综合热度","疑似异常")`,capture.videos.map(v=>[v.bvid,capture.fetchedAt,v.views,v.danmaku,v.replies,v.likes,v.coins,v.favorites,v.heat,null]),'ON CONFLICT(bvid,"抓取时间") DO NOTHING');
 add(`INSERT INTO ranking_video_snapshots (bvid,"榜单分区ID","榜单类型","榜单排名","榜单分数","榜单抓取时间")`,capture.videos.filter(v=>v.rank!==null).map(v=>[v.bvid,0,'all',v.rank,v.score,capture.fetchedAt]),'ON CONFLICT(bvid,"榜单分区ID","榜单类型","榜单抓取时间") DO NOTHING');
 // D1 batch is one transaction: metadata, snapshots, and completion commit together.
 statements.push(db.prepare('INSERT INTO collection_runs (id,fetched_at,source,video_count,saved_at) VALUES (?,?,?,?,?) ON CONFLICT(id) DO NOTHING').bind(capture.id,capture.fetchedAt,capture.source,capture.videos.length,new Date().toISOString()));
 await db.batch(statements);
}

export async function readDashboard(db){
 const videos=await db.prepare(`SELECT v.bvid,v."视频标题" AS title,v."UP主" AS up,v."分区" AS category,v."视频链接" AS url,
 s."播放量" AS views,s."点赞数" AS likes,s."投币数" AS coins,s."收藏数" AS favorites,s."弹幕数" AS danmaku,s."评论数" AS replies,s."综合热度" AS heat,s."抓取时间" AS fetchedAt,
 r."榜单排名" AS rank,r."榜单分数" AS score,o."在线人数" AS online,o."抓取时间" AS onlineFetchedAt
 FROM popular_videos v
 JOIN popular_video_snapshots s ON s.bvid=v.bvid AND s."抓取时间"=(SELECT MAX(fetched_at) FROM collection_runs)
 LEFT JOIN ranking_video_snapshots r ON r.bvid=v.bvid AND r."榜单分区ID"=0 AND r."榜单类型"='all' AND r."榜单抓取时间"=s."抓取时间"
 LEFT JOIN video_online_snapshots o ON o.bvid=v.bvid AND o."抓取时间"=(SELECT MAX("抓取时间") FROM video_online_snapshots WHERE bvid=v.bvid)
 ORDER BY r."榜单排名" IS NULL,r."榜单排名",s."播放量" DESC LIMIT 500`).all();
 const counts=await db.prepare(`SELECT (SELECT COUNT(*) FROM popular_videos) AS videos,(SELECT COUNT(*) FROM popular_video_snapshots) AS snapshots,(SELECT COUNT(*) FROM ranking_video_snapshots) AS rankingSnapshots,(SELECT COUNT(*) FROM video_online_snapshots) AS onlineSnapshots,(SELECT COUNT(*) FROM collection_runs) AS collections`).first();
 const latest=await db.prepare('SELECT fetched_at AS fetchedAt,source,video_count AS videoCount,saved_at AS savedAt FROM collection_runs ORDER BY fetched_at DESC LIMIT 1').first();
 return {storage:'cloud-d1',isDemo:false,videos:videos.results,counts,latest};
}
