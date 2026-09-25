import {test} from 'node:test';
import assert from 'node:assert/strict';
import {sqliteBinding} from '../scripts/local-d1.mjs';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {ensureCapture,readDashboard} from '../server/database.js';
import {handleIngest,validateCapture} from '../server/ingest.js';
const capture=JSON.parse(fs.readFileSync(new URL('../server/capture.json',import.meta.url)));
function migrate(db){for(const f of fs.readdirSync(new URL('../drizzle/',import.meta.url)).filter(f=>f.endsWith('.sql')).sort())db.sqlite.exec(fs.readFileSync(new URL('../drizzle/'+f,import.meta.url),'utf8'))}
test('real capture survives reopening and is idempotent',async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'dynamicdata-db-'));const file=path.join(dir,'test.sqlite');let db=sqliteBinding(file);migrate(db);
 await ensureCapture(db,capture);await ensureCapture(db,capture);const first=await readDashboard(db);
 assert.equal(first.counts.videos,113);assert.equal(first.counts.snapshots,113);assert.equal(first.counts.rankingSnapshots,100);assert.equal(first.counts.collections,1);assert.equal(first.counts.onlineSnapshots,0);
 assert.equal(first.videos.reduce((s,v)=>s+v.views,0),200604020);assert.equal(first.videos.filter(v=>v.rank===null).length,13);assert.ok(first.videos.every(v=>v.online===null));
 db.sqlite.close();db=sqliteBinding(file);const reread=await readDashboard(db);assert.deepEqual(reread,first);db.sqlite.close();fs.unlinkSync(file);fs.rmdirSync(dir);
});
test('interrupted seed resumes without duplicates or falsely reporting completion',async()=>{
 const db=sqliteBinding();migrate(db);const original=db.batch;db.batch=async s=>original([...s.slice(0,2),{run(){throw new Error('temporary storage error')}}]);
 await assert.rejects(ensureCapture(db,capture));assert.equal((await db.prepare('SELECT COUNT(*) AS count FROM collection_runs').first()).count,0);
 assert.equal((await db.prepare('SELECT COUNT(*) AS count FROM popular_video_snapshots').first()).count,0);
 db.batch=original;await ensureCapture(db,capture);assert.equal((await readDashboard(db)).counts.snapshots,113);db.sqlite.close();
});
test('new snapshots retain history and query the latest values',async()=>{
 const db=sqliteBinding();migrate(db);await ensureCapture(db,capture);
 const newer={...capture,id:'newer-test',fetchedAt:'2026-09-13T10:00:00.000Z',videos:[{...capture.videos[0],views:9999999}]};await ensureCapture(db,newer);
 const result=await readDashboard(db);assert.equal(result.counts.snapshots,114);assert.equal(result.counts.collections,2);assert.equal(result.videos.length,1);assert.equal(result.videos.find(v=>v.bvid===newer.videos[0].bvid).views,9999999);db.sqlite.close();
});

const json=(body,status=200)=>Response.json(body,{status});
function incoming(overrides={}){const fetchedAt=new Date().toISOString();return {...capture,id:'scheduled-'+fetchedAt,fetchedAt,popularComplete:true,rankingAvailable:true,...overrides};}
function request(body,token='test-token'){return new Request('https://example.com/api/ingest',{method:'POST',headers:{Authorization:'Bearer '+token},body:JSON.stringify(body)});}

test('ingestion requires a secret, validates records, and rejects stale snapshots',async()=>{
 const db=sqliteBinding();migrate(db);const env={DB:db,SITES_SYNC_TOKEN:'test-token'};const next=incoming();
 assert.equal((await handleIngest(request(next,'wrong'),env,json)).status,401);
 assert.equal((await handleIngest(request(next),{DB:db},json)).status,503);
 assert.equal((await handleIngest(request({...next,videos:[]}),env,json)).status,400);
 assert.equal((await handleIngest(request(next),env,json)).status,200);
 assert.equal((await handleIngest(request(next),env,json)).status,200);
 assert.equal((await readDashboard(db)).counts.collections,1);
 const older=incoming({id:'scheduled-'+capture.fetchedAt,fetchedAt:capture.fetchedAt});
 assert.equal((await handleIngest(request(older),env,json)).status,409);
 assert.throws(()=>validateCapture({...next,videos:[next.videos[0],next.videos[0]]}));
 assert.throws(()=>validateCapture({...next,videos:[{...next.videos[0],views:-1}]}));
 db.sqlite.close();
});

test('unavailable ranking clears current ranks while preserving historical snapshots',async()=>{
 const db=sqliteBinding();migrate(db);await ensureCapture(db,capture);
 const next=incoming({popularComplete:true,rankingAvailable:false,videos:[{...capture.videos[0],title:'Updated title',rank:null,score:null}]});
 assert.equal((await handleIngest(request(next),{DB:db,SITES_SYNC_TOKEN:'test-token'},json)).status,200);
 const result=await readDashboard(db);assert.equal(result.videos.length,1);assert.equal(result.videos[0].rank,null);
 assert.equal(result.videos[0].title,'Updated title');assert.equal(result.counts.rankingSnapshots,100);db.sqlite.close();
});

