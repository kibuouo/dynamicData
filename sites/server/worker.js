import html from '../dist/index.html';
import css from '../dist/style.css';
import js from '../dist/app.js';
import capture from './capture.json';
import {getDb,ensureCapture,readDashboard} from './database.js';
import {handleIngest} from './ingest.js';
const assets={'/':[html,'text/html; charset=utf-8'],'/style.css':[css,'text/css; charset=utf-8'],'/app.js':[js,'text/javascript; charset=utf-8']};
// Keep data values intact after JSON.parse while preventing HTML-like sequences
// in user-controlled video titles from looking like markup to edge security rules.
const json=(body,status=200)=>new Response(JSON.stringify(body).replace(/[<>&\u2028\u2029]/g,character=>({
 '<':'\\u003c','>':'\\u003e','&':'\\u0026','\u2028':'\\u2028','\u2029':'\\u2029'
}[character])),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
export default {async fetch(request,env){
 const url=new URL(request.url);
 if(url.pathname==='/api/ingest')return handleIngest(request,env,json);
 if(request.method!=='GET'&&request.method!=='HEAD')return json({error:'不支持此请求方式'},405);
 if(url.pathname==='/api/videos'){
  try{const db=getDb(env);await ensureCapture(db,capture);const data=await readDashboard(db);return json({...data,updateIntervalHours:6});}
  catch(error){console.error('Cloud database request failed',error);return json({error:'云端数据库暂时无法读取，请稍后重试。'},503);}
 }
 const asset=assets[url.pathname];if(!asset)return new Response('页面不存在',{status:404});
 return new Response(request.method==='HEAD'?null:asset[0],{headers:{'Content-Type':asset[1],'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff','Referrer-Policy':'strict-origin-when-cross-origin'}});
}};
