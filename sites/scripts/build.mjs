import {build} from 'esbuild';
import fs from 'node:fs';
await build({entryPoints:['server/worker.js'],outfile:'dist/server/index.js',bundle:true,format:'esm',platform:'browser',target:'es2022',loader:{'.html':'text','.css':'text'},plugins:[{name:'client-script-as-text',setup(b){b.onLoad({filter:/dist[\\/]app\.js$/},args=>({contents:fs.readFileSync(args.path,'utf8'),loader:'text'}))}}]});
fs.mkdirSync('dist/.openai',{recursive:true});
fs.copyFileSync('.openai/hosting.json','dist/.openai/hosting.json');
fs.cpSync('drizzle','dist/.openai/drizzle',{recursive:true});
console.log('Built Worker with cloud database, page assets, and migrations.');
