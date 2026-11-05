// Loopback-only test boundary. Normal traffic uses the real isolated FastAPI app.
import http from 'node:http';
import {writeFileSync} from 'node:fs';
let mode='normal';
http.createServer((req,res)=>{
  if(req.url==='/__qa/control'){
    let body='';req.on('data',b=>body+=b);req.on('end',()=>{mode=body;writeFileSync('fault-mode.txt',mode);res.end('ok');});return;
  }
  if(req.url==='/__qa/health'){res.end('ok');return;}
  if(req.method==='POST'&&/\/comparison\/advice$/.test(req.url)&&mode==='disconnect') {req.socket.destroy();return;}
  const upstream=http.request({hostname:'127.0.0.1',port:18000,path:req.url,method:req.method,headers:req.headers},reply=>{res.writeHead(reply.statusCode,reply.headers);reply.pipe(res);});
  upstream.on('error',()=>{res.statusCode=502;res.end();});req.pipe(upstream);
}).listen(18001,'127.0.0.1');
