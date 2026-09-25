'use strict';
let data=[],categories=[],loaded=false;
const colors=['#3374f6','#57b7eb','#7e86ed','#f2b958','#a1c4e6'];
const $=id=>document.getElementById(id);
const escapeHTML=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>n===null||n===undefined?'—':n>=1e8?(n/1e8).toFixed(2)+'亿':n>=1e4?(n/1e4).toFixed(1)+'万':Math.round(n).toLocaleString('zh-CN');
function render(){
 const q=$('search').value.trim().toLowerCase(),cat=$('category').value,sort=$('sort').value;
 const filtered=data.filter(v=>(!cat||v.category===cat)&&(!q||(v.title+' '+v.up).toLowerCase().includes(q))).sort((a,b)=>sort==='rank'?(a.rank??Infinity)-(b.rank??Infinity)||(b.views??0)-(a.views??0):(b[sort]??-1)-(a[sort]??-1));
 const total=filtered.reduce((s,v)=>s+(v.views??0),0),heat=filtered.reduce((s,v)=>s+(v.heat??0),0);
 $('count').textContent=loaded?filtered.length:'—';$('views').textContent=loaded?fmt(total):'—';$('average').textContent=loaded?fmt(filtered.length?total/filtered.length:0):'—';$('heat').textContent=filtered.length?(100*heat/filtered.length).toFixed(2)+'%':'—';
 $('result-count').textContent=filtered.length+' 个视频';$('donut-total').textContent=filtered.length;$('table-total').textContent='显示 '+filtered.length+' 条 / 已读取 '+data.length+' 条云端视频';
 $('rows').replaceChildren();filtered.forEach(v=>{const tr=document.createElement('tr');const safeURL=/^BV[a-zA-Z0-9]+$/.test(v.bvid)?'https://www.bilibili.com/video/'+v.bvid:null;
 tr.innerHTML=`<td><span class="${v.rank!==null&&v.rank<=3?'top-rank':'rank'}">${v.rank===null?'—':String(v.rank).padStart(2,'0')}</span></td><td><strong>${safeURL?`<a href="${safeURL}" target="_blank" rel="noreferrer">${escapeHTML(v.title)} ↗</a>`:escapeHTML(v.title)}</strong><small>${escapeHTML(v.up)}</small></td><td><span class="category-pill">${escapeHTML(v.category)}</span></td><td>${fmt(v.views)}</td><td>${fmt(v.likes)}</td><td>${fmt(v.favorites)}</td><td>${fmt(v.online)}</td><td class="heat">${v.heat===null?'—':(v.heat*100).toFixed(2)+'%'}</td>`;$('rows').append(tr)});$('empty').hidden=filtered.length>0||!loaded;
 const counts=categories.map(c=>({name:c,count:filtered.filter(v=>v.category===c).length})).filter(c=>c.count>0).sort((a,b)=>b.count-a.count);
 const groups=counts.length>5?[...counts.slice(0,4),{name:'其他分区',count:counts.slice(4).reduce((s,c)=>s+c.count,0)}]:counts;
 let pos=0;const segments=[];$('legend').replaceChildren();groups.forEach((c,i)=>{const p=filtered.length?c.count/filtered.length*100:0;segments.push(`${colors[i]} ${pos}% ${pos+p}%`);pos+=p;const row=document.createElement('div');row.className='legend-row';row.innerHTML=`<span><i style="background:${colors[i]}"></i>${escapeHTML(c.name)}</span><b>${c.count} <span style="color:#95a0b0">· ${p.toFixed(0)}%</span></b>`;$('legend').append(row)});$('donut').style.background=filtered.length?`conic-gradient(${segments.join(',')})`:'#edf1f7';
 const w=570,h=240,l=56,r=22,t=28,b=42,maxX=Math.max(...filtered.map(v=>v.views??0),1000000)*1.12,maxY=Math.max(...filtered.map(v=>v.likes??0),50000)*1.15;
 let chart=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="播放量与点赞数散点图，${filtered.length} 条视频"><text x="${l}" y="15" fill="#8390a4" font-size="12">点赞数</text>`;
 for(let i=0;i<4;i++){let y=t+(h-t-b)*i/3;chart+=`<line x1="${l}" y1="${y}" x2="${w-r}" y2="${y}" stroke="#e9eef6" stroke-dasharray="3 4"/><text x="${l-10}" y="${y+4}" text-anchor="end" fill="#8390a4" font-size="12">${fmt(maxY*(3-i)/3)}</text>`}
 for(let i=0;i<5;i++){let x=l+(w-l-r)*i/4;chart+=`<text x="${x}" y="${h-21}" text-anchor="middle" fill="#8390a4" font-size="12">${fmt(maxX*i/4)}</text>`}
 filtered.forEach(v=>{if(v.views===null||v.likes===null)return;const x=l+v.views/maxX*(w-l-r),y=h-b-v.likes/maxY*(h-t-b);chart+=`<circle cx="${x}" cy="${y}" r="6" fill="#3374f6" opacity=".65" stroke="white" stroke-width="1.5"><title>${escapeHTML(v.title)}：播放 ${fmt(v.views)}，点赞 ${fmt(v.likes)}</title></circle>`});chart+=`<text x="${w-r}" y="${h-3}" text-anchor="end" fill="#8390a4" font-size="12">播放量</text></svg>`;$('scatter').innerHTML=chart;
}
async function loadData(){
 $('reload').disabled=true;$('cloud-pill').textContent='正在读取';$('cloud-message').textContent=loaded?'正在重新读取云端数据…':'正在连接云端数据库，首次载入可能需要一点时间…';
 try{const response=await fetch('/api/videos',{cache:'no-store',signal:AbortSignal.timeout(60000)});const result=await response.json();if(!response.ok||!Array.isArray(result.videos)||result.storage!=='cloud-d1')throw new Error(result.error||'数据读取失败');
 data=result.videos;loaded=true;categories=[...new Set(data.map(v=>v.category))].sort((a,b)=>a.localeCompare(b,'zh-CN'));
 const selection=$('category').value;$('category').replaceChildren();const all=document.createElement('option');all.value='';all.textContent='全部分区';$('category').append(all);categories.forEach(c=>{const o=document.createElement('option');o.value=o.textContent=c;$('category').append(o)});$('category').value=categories.includes(selection)?selection:'';
 const stale=Date.now()-Date.parse(result.latest.fetchedAt)>8*3600000;
 $('cloud-pill').textContent=stale?'数据待更新':'云端已连接';const time=new Date(result.latest.fetchedAt).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});$('cloud-message').textContent=`本次 ${data.length} 条视频 · 累计 ${result.counts.snapshots} 条互动快照 · ${result.counts.rankingSnapshots} 条榜单快照。最近采集：${time}（北京时间）。每 6 小时自动更新${stale?'；更新可能延迟，当前展示上次成功数据':''}。`;
 const notices=[];
 if((result.latest.source||'').includes('partial'))notices.push('热门列表本次只采集到部分数据');
 if(!data.some(v=>v.rank!==null))notices.push('排行榜本次不可用');
 $('data-note').textContent=(notices.length?notices.join('；'):'云端保存的真实采集数据')+' · 在线人数未采集';render();
 }catch(error){$('cloud-pill').textContent='读取失败';$('cloud-message').textContent=loaded?'暂时无法读取云端数据，当前保留上次已加载的结果。请点击重新读取。':'暂时无法读取云端数据，请点击重新读取重试。';if(!loaded)$('table-total').textContent='数据尚未载入';}
 finally{$('reload').disabled=false;}
}
['search','category','sort'].forEach(id=>$(id).addEventListener(id==='search'?'input':'change',render));$('reset').addEventListener('click',()=>{$('search').value='';$('category').value='';$('sort').value='rank';render()});$('reload').addEventListener('click',loadData);
document.querySelectorAll('nav a').forEach(a=>a.addEventListener('click',()=>{document.querySelectorAll('nav a').forEach(n=>n.classList.remove('active'));a.classList.add('active')}));render();loadData();
// Only reread saved cloud data; opening a page never triggers upstream scraping.
setInterval(()=>{if(!document.hidden&&!$('reload').disabled)loadData();},5*60*1000);

