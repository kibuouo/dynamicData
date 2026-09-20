import fs from 'node:fs';
import crypto from 'node:crypto';
const work=new URL('../../../work/',import.meta.url);
const read=name=>JSON.parse(fs.readFileSync(new URL(name,work),'utf8').replace(/^\uFEFF/,''));
const popular=read('bilibili-popular-raw.json'),ranking=read('bilibili-ranking-raw.json');
if(popular.code!==0||ranking.code!==0||!popular.data.list.length||!ranking.data.list.length)throw new Error('Incomplete Bilibili capture');
const fetchedAt=fs.statSync(new URL('bilibili-ranking-raw.json',work)).mtime.toISOString();
const rankMap=new Map(ranking.data.list.map((v,i)=>[v.bvid,{rank:i+1,score:Number.isFinite(v.score)?v.score:null}]));
const combined=new Map([...ranking.data.list,...popular.data.list].map(v=>[v.bvid,v]));
const videos=[...combined.values()].map(v=>{
 const s=v.stat;for(const k of ['view','like','coin','favorite','danmaku','reply'])if(!Number.isSafeInteger(s[k])||s[k]<0)throw new Error('Invalid '+k);
 return {bvid:v.bvid,aid:v.aid,cid:v.cid,title:v.title,up:v.owner.name,category:v.tname,
 pubDate:new Date(v.pubdate*1000).toISOString(),url:'https://www.bilibili.com/video/'+v.bvid,cover:v.pic,duration:v.duration,
 views:s.view,likes:s.like,coins:s.coin,favorites:s.favorite,danmaku:s.danmaku,replies:s.reply,
 heat:s.view?(s.like*.4+s.coin*.1+s.favorite*.1+s.danmaku*.4)/s.view:0,
 rank:rankMap.get(v.bvid)?.rank??null,score:rankMap.get(v.bvid)?.score??null};
});
const capture={id:'capture-'+crypto.createHash('sha256').update(JSON.stringify({videos,fetchedAt})).digest('hex').slice(0,24),fetchedAt,
 source:'Bilibili 热门列表 + 全站排行榜',sources:['https://api.bilibili.com/x/web-interface/popular?pn=1&ps=20','https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all'],popularCount:popular.data.list.length,rankingCount:ranking.data.list.length,videos};
fs.writeFileSync(new URL('../server/capture.json',import.meta.url),JSON.stringify(capture,null,2)+'\n');
console.log(JSON.stringify({videos:videos.length,popular:capture.popularCount,ranking:capture.rankingCount,fetchedAt,totalViews:videos.reduce((s,v)=>s+v.views,0)}));
