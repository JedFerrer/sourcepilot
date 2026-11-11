// Prototype presentation checks; uses the repository's existing Playwright install.
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';
import fs from 'node:fs/promises';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../../..');
const require=createRequire(path.join(root,'apps/web/package.json'));
const {chromium}=require('@playwright/test');
const output=path.resolve(process.argv[2]||path.join(root,'.local-investigation-artifacts/UX-U1',`visual-${Date.now()}`));
assert(output.startsWith(path.join(root,'.local-investigation-artifacts')+path.sep));
await fs.mkdir(output,{recursive:true});
assert(!(await fs.access(path.join(output,'visual-report.json')).then(()=>true,()=>false)));
const browser=await chromium.launch({channel:'chrome',headless:true});
const page=await browser.newPage();
const checks=[],measurements=[],focus=[],errors=[],network=[];
page.on('pageerror',e=>errors.push(String(e)));
page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(r.url());});
const url=(stage,scenario='normal')=>pathToFileURL(path.join(here,'index.html')).href+`?stage=${stage}&scenario=${scenario}`;
try{
  for(const width of [1440,768,390,320]){
    await page.setViewportSize({width,height:900});
    for(const scheme of ['light','dark']){
      await page.emulateMedia({colorScheme:scheme});
      for(const stage of ['dashboard','brief','suppliers','quotes','comparison','decision']){
        await page.goto(url(stage));
        const result=await page.evaluate(()=>{
          const rgb=c=>(c.match(/[\d.]+/g)||[]).map(Number);
          const lum=c=>rgb(c).slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
          const ratio=(a,b)=>(Math.max(lum(a),lum(b))+.05)/(Math.min(lum(a),lum(b))+.05);
          const bg=el=>{for(let e=el;e;e=e.parentElement){const c=getComputedStyle(e).backgroundColor;if(rgb(c).length===3||rgb(c)[3]===1)return c;}return 'rgb(255,255,255)';};
          const visible=el=>el.checkVisibility({checkVisibilityCSS:true})&&!el.closest('.sr-only')&&!el.matches('.skip');
          const text=[...document.querySelectorAll('body *')].filter(el=>visible(el)&&!el.closest(':disabled')&&[...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&!['SCRIPT','STYLE','OPTION','NOSCRIPT'].includes(el.tagName)).map(el=>{
            const s=getComputedStyle(el);return {text:el.textContent.trim().slice(0,70),size:parseFloat(s.fontSize),ratio:ratio(s.color,bg(el)),selector:el.tagName+'.'+el.className};
          });
          return {
            html:{scheme:getComputedStyle(document.documentElement).colorScheme,bg:getComputedStyle(document.documentElement).backgroundColor},
            body:{scheme:getComputedStyle(document.body).colorScheme,bg:getComputedStyle(document.body).backgroundColor},
            overflow:document.documentElement.scrollWidth>innerWidth+1,
            minTextSize:Math.min(...text.map(t=>t.size)),
            minTextContrast:Math.min(...text.map(t=>t.ratio)),
            contrastFailures:text.filter(t=>t.ratio<4.5),
            smallText:text.filter(t=>t.size<13),
            inputSizes:[...document.querySelectorAll('input,select,textarea')].filter(visible).map(el=>getComputedStyle(el).fontSize),
            sideBorders:[...document.querySelectorAll('.notice,.advice,.paper mark')].filter(visible).map(el=>getComputedStyle(el).borderLeftWidth)
          };
        });
        measurements.push({width,scheme,stage,...result});
        assert(!result.overflow,`${stage} overflow ${width}`);
        for(const surface of [result.html,result.body]){assert(surface.scheme.includes('light')&&!surface.scheme.includes('dark'));assert.equal(surface.bg,'rgb(245, 246, 248)');}
        assert.equal(result.smallText.length,0,JSON.stringify(result.smallText));
        assert.equal(result.contrastFailures.length,0,JSON.stringify(result.contrastFailures));
        assert(result.inputSizes.every(s=>s==='16px'));
        assert(result.sideBorders.every(w=>parseFloat(w)<=1));
      }
    }
    await page.goto(url('quotes'));
    await page.keyboard.press('Tab'); // Skip link
    await page.keyboard.press('Tab'); // Review controls
    const f=await page.evaluate(()=>{const el=document.activeElement,s=getComputedStyle(el),r=el.getBoundingClientRect();return {text:el.textContent,outline:s.outline,top:r.top,bottom:r.bottom,width:r.width};});
    assert(['3px','solid','rgb(36, 87, 197)'].every(part=>f.outline.includes(part)),JSON.stringify(f));
    assert(f.top>=0&&f.bottom<=900);focus.push({width,...f});
    await page.screenshot({path:path.join(output,`keyboard-focus-${width}.png`)});
    for(const selector of ['button.evidence-trigger','button.secondary','button.tertiary','button[data-action="save"]',...(width>=768?['.supplier-switch button']:[])]){
      const control=page.locator(selector).filter({visible:true}).first();
      await control.hover();
      const colors=await control.evaluate(el=>{const s=getComputedStyle(el);return {color:s.color,background:s.backgroundColor};});
      assert(colors.background!=='rgb(25, 69, 162)'||colors.color==='rgb(255, 255, 255)',`Unreadable primary hover: ${selector}`);
    }
    for(const [stage,scenario] of [['comparison','three'],['quotes','failed'],['brief','blocked']]){
      await page.goto(url(stage,scenario));
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.screenshot({path:path.join(output,`${stage}-${scenario}-${width}.png`),fullPage:true});
    }
  }
  checks.push('48 screen/width/color-preference combinations: explicit light surfaces, no overflow, visible text >=13px and sampled text contrast >=4.5:1, inputs 16px, no decorative side rails');
  checks.push('Visible keyboard focus and legible action hover treatments at all four widths; 12 warning/state full-page captures');
  await page.goto(pathToFileURL(path.join(here,'layouts.html')).href);
  assert(await page.evaluate(()=>['html','body'].every(s=>getComputedStyle(document.querySelector(s)).colorScheme.includes('light'))));
  assert.equal(network.length,0);assert.equal(errors.length,0);
  checks.push('Atlas light theme; no external requests or browser errors');
}catch(e){errors.push(String(e));process.exitCode=1;await page.screenshot({path:path.join(output,'visual-failure.png'),fullPage:true});}
finally{
  const hashes={};for(const name of ['index.html','prototype.css','prototype.js','layouts.html','verify-visual.mjs'])hashes[name]=crypto.createHash('sha256').update(await fs.readFile(path.join(here,name))).digest('hex');
  await fs.writeFile(path.join(output,'visual-report.json'),JSON.stringify({scope:'Controlled Chrome prototype presentation checks, not full WCAG certification; text contrast uses opaque ancestor backgrounds, excludes disabled and visually hidden text',checks,measurements,focus,errors,network,hashes},null,2));
  console.log(JSON.stringify({output,checks,errors},null,2));await browser.close();
}
