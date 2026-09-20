import {DatabaseSync} from 'node:sqlite';
export function sqliteBinding(file=':memory:'){
 const sqlite=new DatabaseSync(file);
 const db={sqlite,prepare(sql){const stmt=sqlite.prepare(sql);const make=values=>({bind(...v){return make(v)},async first(){return stmt.get(...values)??null},async all(){return {results:stmt.all(...values)}},async run(){return stmt.run(...values)}});return make([])},async batch(statements){sqlite.exec('BEGIN');try{const out=[];for(const s of statements)out.push(await s.run());sqlite.exec('COMMIT');return out}catch(e){sqlite.exec('ROLLBACK');throw e}}};
 return db;
}
