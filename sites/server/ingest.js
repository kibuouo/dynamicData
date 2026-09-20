import {ensureCapture,getDb} from './database.js';

const MAX_BYTES=2_000_000;
export function validateCapture(capture){
 if(!capture||!Array.isArray(capture.videos)||!capture.videos.length||capture.videos.length>500)throw new Error('需要 1–500 条视频');
 const time=Date.parse(capture.fetchedAt);
 if(!Number.isFinite(time)||new Date(time).toISOString()!==capture.fetchedAt||time>Date.now()+600_000)throw new Error('采集时间无效');
 if(capture.id!=='scheduled-'+capture.fetchedAt)throw new Error('快照标识无效');
 if(typeof capture.source!=='string'||capture.source.length>200)throw new Error('数据来源无效');
 const ids=new Set();
 for(const v of capture.videos){
  if(!v||!/^BV[a-zA-Z0-9]{10}$/.test(v.bvid)||ids.has(v.bvid))throw new Error('视频编号无效或重复');
  ids.add(v.bvid);
  for(const key of ['title','up','category','pubDate','url','cover']){
   if(v[key]!==null&&(typeof v[key]!=='string'||v[key].length>2000))throw new Error('文本字段无效');
  }
  if(!v.title?.trim())throw new Error('视频标题不能为空');
  for(const key of ['aid','cid','duration','views','danmaku','replies','likes','coins','favorites']){
   if(v[key]!==null&&(!Number.isSafeInteger(v[key])||v[key]<0))throw new Error('视频计数无效');
  }
  if(!Number.isSafeInteger(v.views)||v.views<=0)throw new Error('播放量无效');
  for(const key of ['heat','score'])if(v[key]!==null&&(!Number.isFinite(v[key])||v[key]<0))throw new Error('指标无效');
  if(v.rank!==null&&(!Number.isInteger(v.rank)||v.rank<1||v.rank>100))throw new Error('榜单排名无效');
 }
 if(typeof capture.rankingAvailable!=='boolean'||capture.rankingAvailable!==capture.videos.some(v=>v.rank!==null))throw new Error('排行榜状态不一致');
 return capture;
}

export async function handleIngest(request,env,json){
 if(request.method!=='POST')return json({error:'请使用 POST'},405);
 if(!env.SITES_SYNC_TOKEN)return json({error:'同步尚未配置'},503);
 // Hash both strings before comparison so token length and prefix are not disclosed.
 const digest=async value=>new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)));
 const [actual,expected]=await Promise.all([digest(request.headers.get('Authorization')||''),digest('Bearer '+env.SITES_SYNC_TOKEN)]);
 let different=0;for(let i=0;i<actual.length;i++)different|=actual[i]^expected[i];
 if(different)return json({error:'未授权'},401);
 if(Number(request.headers.get('Content-Length'))>MAX_BYTES)return json({error:'数据过大'},413);
 let capture;
 try{
  const bytes=await request.arrayBuffer();if(bytes.byteLength>MAX_BYTES)return json({error:'数据过大'},413);
  capture=validateCapture(JSON.parse(new TextDecoder().decode(bytes)));
 }catch(error){return json({error:error.message},400);}
 try{
  const db=getDb(env);
  const existing=await db.prepare('SELECT id FROM collection_runs WHERE id = ?').bind(capture.id).first();
  if(!existing){
   const latest=await db.prepare('SELECT MAX(fetched_at) AS fetchedAt FROM collection_runs').first();
   if(latest?.fetchedAt>=capture.fetchedAt)return json({error:'拒绝过期快照'},409);
   await ensureCapture(db,capture);
  }
  return json({success:true,id:capture.id,videoCount:capture.videos.length,fetchedAt:capture.fetchedAt});
 }catch(error){console.error('Cloud sync failed',error);return json({error:'同步未完成，已有数据保持不变'},503);}
}
