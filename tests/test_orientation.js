// Testes independentes do navegador; sem bibliotecas extras.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(require('path').join(__dirname,'../static/app.js'),'utf8');
const cut=source.split('loadCluster();setInterval')[0];
const context={console,setTimeout,clearTimeout,setInterval(){},clearInterval(){},WebSocket:{OPEN:1},sessionStorage:{getItem(){return null}},location:{protocol:'http:',host:'localhost'},document:{getElementById(){return {classList:{add(){},remove(){},toggle(){}},textContent:'',replaceChildren(){}}},querySelectorAll(){return []}}};
vm.createContext(context);vm.runInContext(cut,context);
const query=e=>vm.runInContext(e,context);
const pairs=[
 [[0,0],'w',[0,0]],[[7,7],'w',[7,7]],[[0,0],'b',[7,7]],[[7,7],'b',[0,0]],
 [[0,7],'b',[7,0]],[[3,5],'b',[4,2]],[[6,4],'b',[1,3]]];
for(const [visual,side,expected] of pairs){const actual=query(`visualToLogical(${visual[0]},${visual[1]},'${side}')`);assert.deepStrictEqual(Array.from(actual),expected);}
for(const side of ['w','b'])for(let r=0;r<8;r++)for(let c=0;c<8;c++){
 const [rr,cc]=query(`visualToLogical(${r},${c},'${side}')`);
 assert.equal((rr+cc)%2,(r+c)%2,'cores de casas preservadas');
 assert.ok(rr>=0&&rr<8&&cc>=0&&cc<8);
}
assert.equal(query("orientationFor('w')"),'white');
assert.equal(query("orientationFor('b')"),'black');
assert.equal(query("boardCoordinates(7,0,'w').file"),'a');
assert.equal(query("boardCoordinates(7,0,'w').rank"),'1');
assert.equal(query("boardCoordinates(0,7,'b').file"),'h');
assert.equal(query("boardCoordinates(0,7,'b').rank"),'8');
assert.equal(query("squareName(...visualToLogical(0,0,'b'))"),'h1');
assert.equal(query("squareName(...visualToLogical(7,7,'b'))"),'a8');
assert.equal(query("squareName(...visualToLogical(7,0,'w'))"),'a1');
console.log('OK: orientação, 64 casas, paridade, coordenadas e cores.');
