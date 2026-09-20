import http from 'node:http';
import fs from 'node:fs';
import worker from '../dist/server/index.js';
import {sqliteBinding} from './local-d1.mjs';
fs.mkdirSync('.local',{recursive:true});const fresh=!fs.existsSync('.local/preview.sqlite');const DB=sqliteBinding('.local/preview.sqlite');
if(fresh)for(const f of fs.readdirSync('drizzle').filter(f=>f.endsWith('.sql')).sort())DB.sqlite.exec(fs.readFileSync('drizzle/'+f,'utf8'));
http.createServer(async(req,res)=>{try{const result=await worker.fetch(new Request('http://127.0.0.1:5173'+req.url,{method:req.method,headers:req.headers}),{DB});res.writeHead(result.status,Object.fromEntries(result.headers));res.end(Buffer.from(await result.arrayBuffer()))}catch(e){res.writeHead(500);res.end('Preview failed');console.error(e)}}).listen(5173,'127.0.0.1',()=>console.log('Local: http://127.0.0.1:5173/'));
