#!/usr/bin/env python3
"""Erzeugt ein bearbeitbares Kurs-Editor-Widget (show_widget-Format) aus einer
moodle-mbz-builder Kurs-JSON. Round-Trip: Aktionen senden den vollen Kursstand
als JSON-Envelope via sendPrompt an Claude (siehe SKILL.md, Abschnitt
"Interaktiver Kurs-Editor")."""
import argparse, copy, json, os, re

MAX_WIDGET_CHARS = 300_000
RASTER = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
          ".gif": "image/gif", ".webp": "image/webp"}


def _inline_image_map(act):
    """SVG-Markup / Data-URIs fuer die Bild-Vorschau, unter _-Key (wird beim
    Senden vom Widget entfernt — Bilder reisen nie im Envelope)."""
    import base64
    m = {}
    for img in act.get("images", []):
        path = img if isinstance(img, str) else img.get("file")
        if not path or not os.path.exists(path):
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext == ".svg":
            svg = re.sub(r"<\?xml[^>]*\?>", "",
                         open(path, encoding="utf-8").read()).strip()
            m[os.path.basename(path)] = svg
        elif ext in RASTER:
            data = base64.b64encode(open(path, "rb").read()).decode()
            m[os.path.basename(path)] = (
                f"<img src='data:{RASTER[ext]};base64,{data}' style='max-width:100%'>")
    return m


def _enrich(spec, inline_images):
    s = copy.deepcopy(spec)
    if inline_images:
        for sec in s.get("sections", []):
            for act in sec.get("activities", []):
                imap = _inline_image_map(act)
                if imap:
                    act["_inline_images"] = imap
    return s


def build_widget(spec, inline_images=True):
    enriched = _enrich(spec, inline_images)
    data = json.dumps(enriched, ensure_ascii=False).replace("</", "<\\/")
    out = TEMPLATE.replace("__COURSE_JSON__", data)
    if inline_images and len(out) > MAX_WIDGET_CHARS:
        return build_widget(spec, inline_images=False)
    return out


TEMPLATE = r"""<h2 class="sr-only" style="position:absolute;left:-9999px">Bearbeitbarer Moodle-Kurs-Editor: Abschnitte und Aktivitaeten aendern, KI-Auftraege ausloesen, Kurs fertigstellen</h2>
<div id="mbz-editor" style="color:var(--text-primary)">
<div id="ed-head" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:2px">
  <span id="ed-title" style="font-size:17px;font-weight:500"></span>
  <span id="dirty-badge" style="display:none;font-size:12px;background:var(--bg-warning);color:var(--text-warning);padding:2px 10px;border-radius:var(--radius)">ungespeichert</span>
  <span style="flex:1"></span>
  <button onclick="ED.send('save')"><i class="ti ti-device-floppy" aria-hidden="true" style="font-size:16px;vertical-align:-2px;margin-right:5px"></i>Speichern ↗</button>
  <button onclick="ED.send('video_recap')"><i class="ti ti-movie" aria-hidden="true" style="font-size:16px;vertical-align:-2px;margin-right:5px"></i>Video-Recap ↗</button>
  <button onclick="ED.send('finalize')"><i class="ti ti-package-export" aria-hidden="true" style="font-size:16px;vertical-align:-2px;margin-right:5px"></i>Fertigstellen → .mbz ↗</button>
</div>
<div id="ed-meta" style="font-size:13px;color:var(--text-secondary);margin-bottom:12px"></div>
<div id="ed-sections"></div>
<button style="margin-top:8px" onclick="ED.addSection()"><i class="ti ti-plus" aria-hidden="true" style="font-size:16px;vertical-align:-2px;margin-right:5px"></i>Abschnitt hinzufügen</button>
</div>
<style>
#mbz-editor .sec{border:0.5px solid var(--border);border-radius:12px;margin-bottom:8px;overflow:hidden;background:var(--surface-2)}
#mbz-editor .sec-h{display:flex;align-items:center;gap:8px;padding:9px 12px;background:var(--surface-1);cursor:pointer}
#mbz-editor .act{border-top:0.5px solid var(--border);padding:7px 12px}
#mbz-editor .act-h{display:flex;align-items:center;gap:8px;cursor:pointer;font-size:14px}
#mbz-editor textarea{width:100%;box-sizing:border-box}
#mbz-editor .mini{border:none;background:none;cursor:pointer;font-size:14px;padding:2px 5px;color:var(--text-secondary)}
#mbz-editor .mini:hover{color:var(--text-primary)}
#mbz-editor .chip{font-size:12px;background:var(--surface-1);padding:1px 9px;border-radius:var(--radius);color:var(--text-secondary)}
#mbz-editor .fld{margin:7px 0}
#mbz-editor .fld>label{display:block;font-size:12px;color:var(--text-secondary);margin-bottom:2px}
#mbz-editor .rich{border:0.5px solid var(--border);border-radius:var(--radius);padding:7px 9px;min-height:2em;font-size:13.5px;line-height:1.55;background:var(--surface-2);cursor:text}
#mbz-editor .rich:focus{outline:none;box-shadow:0 0 0 1px var(--border-accent)}
#mbz-editor .rich h1,#mbz-editor .rich h2,#mbz-editor .rich h3{font-size:15px;font-weight:500;margin:6px 0 3px}
#mbz-editor .rich p{margin:4px 0}
#mbz-editor .rich ul,#mbz-editor .rich ol{margin:4px 0;padding-left:20px}
#mbz-editor .rich img,#mbz-editor .rich svg{max-width:100%;height:auto}
#mbz-editor .rich table{border-collapse:collapse;font-size:12.5px;margin:6px 0;width:100%}
#mbz-editor .rich td,#mbz-editor .rich th{border:0.5px solid var(--border-strong,#999);padding:4px 7px;text-align:left}
#mbz-editor .svgwrap{display:block;text-align:center;margin:8px 0;border:0.5px dashed var(--border);border-radius:var(--radius);padding:4px}
#mbz-editor .ai-row{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px;padding-top:8px;border-top:0.5px dashed var(--border)}
</style>
<script type="application/json" id="course-data">__COURSE_JSON__</script>
<script>
window.ED = (function(){
const COURSE = JSON.parse(document.getElementById('course-data').textContent);
let dirty = false;
const open = {sec:{}, act:{}};
function setDirty(v){dirty=v;document.getElementById('dirty-badge').style.display=v?'inline-block':'none';}
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
function stripPrivate(o){
  if(Array.isArray(o))return o.map(stripPrivate);
  if(o&&typeof o==='object'){const r={};for(const k in o){if(!k.startsWith('_'))r[k]=stripPrivate(o[k]);}return r;}
  return o;
}
function send(action, extra){
  const env=Object.assign({widget:'mbz-course-editor',action:action,course:stripPrivate(COURSE)},extra||{});
  sendPrompt('Kurs-Editor-Aktion:\n```json\n'+JSON.stringify(env)+'\n```');
  if(action==='save')setDirty(false);
}
const TYPES=["label","page","url","resource","folder","book","assign","forum","glossary","choice","feedback","quiz"];
const TLABEL={label:"Textfeld",page:"Seite",url:"Link",resource:"Datei",folder:"Ordner",book:"Buch",assign:"Aufgabe",forum:"Forum",glossary:"Glossar",choice:"Abstimmung",feedback:"Feedback",quiz:"Test"};
function icon(n){return '<i class="ti ti-'+n+'" aria-hidden="true" style="font-size:15px;vertical-align:-2px"></i>';}
function secs(){return COURSE.sections=COURSE.sections||[];}
function moveSection(i,d){const s=secs(),j=i+d;if(j<0||j>=s.length)return;const t=s[i];s[i]=s[j];s[j]=t;setDirty(true);render();}
function delSection(i){if(!confirm('Abschnitt "'+(secs()[i].name||i)+'" löschen?'))return;secs().splice(i,1);setDirty(true);render();}
function addSection(){secs().push({name:"Neuer Abschnitt",summary:"",activities:[]});open.sec[secs().length-1]=true;setDirty(true);render();}
function moveAct(si,ai,d){const a=secs()[si].activities,j=ai+d;if(j<0||j>=a.length)return;const t=a[ai];a[ai]=a[j];a[j]=t;setDirty(true);render();}
function delAct(si,ai){const a=secs()[si].activities;if(!confirm('Aktivität "'+(a[ai].name||a[ai].type)+'" löschen?'))return;a.splice(ai,1);setDirty(true);render();}
function addActivity(si,type){const a=secs()[si].activities=secs()[si].activities||[];
  const nu={type:type,name:"Neue "+(TLABEL[type]||type)};
  if(type==="page")nu.content="<p></p>";if(type==="quiz")nu.questions=[];
  if(type==="glossary")nu.entries=[];if(type==="choice")nu.options=[];
  if(type==="folder")nu.files=[];if(type==="book")nu.chapters=[];
  if(type==="feedback")nu.items=[];if(type==="url")nu.externalurl="https://";
  if(type==="resource")nu.file="";
  a.push(nu);open.sec[si]=true;open.act[si+"_"+(a.length-1)]=true;setDirty(true);render();}
function render(){
  document.getElementById('ed-title').textContent=(COURSE.course||{}).fullname||'Kurs';
  const nAct=secs().reduce(function(s,x){return s+(x.activities||[]).length;},0);
  document.getElementById('ed-meta').textContent=secs().length+' Abschnitte · '+nAct
    +' Aktivitäten · Format: '+((COURSE.course||{}).format||'topics')
    +' — Abschnitt anklicken, Aktivität aufklappen, direkt in der Ansicht editieren.';
  const root=document.getElementById('ed-sections');root.innerHTML='';
  secs().forEach(function(sec,si){
    const sd=document.createElement('div');sd.className='sec';sd.dataset.si=si;
    const hidden=sec.visible===0?' <span class="chip">verborgen</span>':'';
    sd.innerHTML='<div class="sec-h"><span class="schev">'+icon(open.sec[si]?'chevron-down':'chevron-right')+'</span>'
      +'<input value="'+esc(sec.name||('Abschnitt '+si))+'" data-role="secname" style="flex:1;font-weight:500;border:none;background:transparent;box-shadow:none">'
      +hidden+'<span class="chip">'+(sec.activities||[]).length+' Akt.</span>'
      +'<button class="mini" data-op="secup" aria-label="Abschnitt nach oben">'+icon('arrow-up')+'</button>'
      +'<button class="mini" data-op="secdown" aria-label="Abschnitt nach unten">'+icon('arrow-down')+'</button>'
      +'<button class="mini" data-op="secdel" aria-label="Abschnitt löschen">'+icon('trash')+'</button></div>'
      +'<div class="sec-b" style="display:'+(open.sec[si]?'block':'none')+'"></div>';
    const body=sd.querySelector('.sec-b');
    (sec.activities||[]).forEach(function(act,ai){
      const key=si+'_'+ai;
      const ad=document.createElement('div');ad.className='act';ad.dataset.si=si;ad.dataset.ai=ai;
      ad.innerHTML='<div class="act-h"><span class="achev">'+icon(open.act[key]?'chevron-down':'chevron-right')+'</span>'
        +'<span style="flex:1">'+esc(act.name||act.type)+'</span><span class="chip">'+(TLABEL[act.type]||act.type)+'</span>'
        +'<button class="mini" data-op="actup" aria-label="nach oben">'+icon('arrow-up')+'</button>'
        +'<button class="mini" data-op="actdown" aria-label="nach unten">'+icon('arrow-down')+'</button>'
        +'<button class="mini" data-op="actdel" aria-label="löschen">'+icon('trash')+'</button></div>'
        +'<div class="act-body" style="display:'+(open.act[key]?'block':'none')+'"></div>';
      if(open.act[key])renderEditor(si,ai,ad.querySelector('.act-body'));
      body.appendChild(ad);
    });
    const addRow=document.createElement('div');addRow.className='act';
    addRow.innerHTML='<select data-role="addtype">'+TYPES.map(function(t){return '<option value="'+t+'">'+TLABEL[t]+'</option>';}).join('')+'</select> '
      +'<button data-op="actadd">'+icon('plus')+' Aktivität</button>';
    body.appendChild(addRow);
    root.appendChild(sd);
  });
}
document.getElementById('mbz-editor').addEventListener('click',function(e){
  const btn=e.target.closest('[data-op]');
  const op=btn?btn.dataset.op:null;
  const secEl=e.target.closest('.sec[data-si]');if(!secEl)return;
  const si=+secEl.dataset.si;const actEl=e.target.closest('.act[data-ai]');
  const ai=actEl?+actEl.dataset.ai:null;
  if(op==='secup')return moveSection(si,-1);if(op==='secdown')return moveSection(si,1);
  if(op==='secdel')return delSection(si);
  if(op==='actup')return moveAct(si,ai,-1);if(op==='actdown')return moveAct(si,ai,1);
  if(op==='actdel')return delAct(si,ai);
  if(op==='actadd')return addActivity(si,secEl.querySelector('[data-role=addtype]').value);
  if(e.target.closest('.sec-h')&&!(e.target.dataset&&e.target.dataset.role)){open.sec[si]=!open.sec[si];return render();}
  if(e.target.closest('.act-h')){const k=si+'_'+ai;open.act[k]=!open.act[k];return render();}
});
document.getElementById('mbz-editor').addEventListener('input',function(e){
  const r=e.target.dataset&&e.target.dataset.role;
  if(r==='secname'){const si=+e.target.closest('.sec').dataset.si;secs()[si].name=e.target.value;setDirty(true);}
});
function fld(label,inputHtml){return '<div class="fld"><label>'+label+'</label>'+inputHtml+'</div>';}
function ta(val,rows){return '<textarea rows="'+(rows||4)+'">'+esc(val)+'</textarea>';}
function rich(val){return '<div class="rich" contenteditable="true">'+(val||'<p></p>')+'</div>';}
function inlineImgs(a,html){
  if(!a._inline_images)return html;
  return String(html||'').replace(/<img[^>]*@@PLUGINFILE@@\/([^'"]+)['"][^>]*>/g,function(m,name){
    const im=a._inline_images[name];
    return im?'<span class="svgwrap" data-pf="'+name+'" contenteditable="false">'+im+'</span>':m;
  });
}
function serializeRich(el){
  const c=el.cloneNode(true);
  c.querySelectorAll('.svgwrap').forEach(function(w){
    const img=document.createElement('img');
    img.setAttribute('src','@@PLUGINFILE@@/'+w.dataset.pf);
    img.setAttribute('style','max-width:100%;height:auto;');
    w.replaceWith(img);
  });
  return c.innerHTML;
}
function bindRich(scope,idx,fn){const r=scope.querySelectorAll('.rich')[idx];if(r)r.addEventListener('input',function(){fn(serializeRich(this));setDirty(true);});return r;}
function bind(el,sel,fn){el.querySelectorAll(sel).forEach(fn);}
function edPage(a,el){
  el.insertAdjacentHTML('beforeend',
    fld('Inhalt (Diagramme inline; Neuzeichnen via KI-Auftrag)',rich(inlineImgs(a,a.content)))
    +fld('Infoblatt (material)','<input type="checkbox" '+(a.material?'checked':'')+' data-f="material" style="width:auto">')
    +fld('Kernpunkte (eine pro Zeile, optional)',ta((a.material_bullets||[]).join('\n'),3)));
  bindRich(el,0,function(v){a.content=v;});
  el.querySelector('textarea').addEventListener('input',function(){a.material_bullets=this.value.split('\n').filter(Boolean);setDirty(true);});
  el.querySelector('[data-f=material]').addEventListener('change',function(){a.material=this.checked;setDirty(true);});
}
function edQuiz(a,el){
  a.questions=a.questions||[];
  a.questions.forEach(function(q,qi){
    const qd=document.createElement('div');
    qd.style.cssText='border:0.5px solid var(--border);border-radius:var(--radius);padding:8px 10px;margin:8px 0';
    let inner=fld('Frage '+(qi+1)+' ('+(q.type||'multichoice')+')',rich(q.questiontext))
      +fld('Erklärung (für alle nach dem Antworten)',rich(q.generalfeedback));
    if(q.type==='truefalse'){
      inner+=fld('Richtig?','<select data-q="correct"><option value="true"'+(q.correct?' selected':'')+'>Wahr</option><option value="false"'+(!q.correct?' selected':'')+'>Falsch</option></select>')
        +fld('Feedback richtig',rich(q.feedbackcorrect))+fld('Feedback falsch',rich(q.feedbackwrong));
    }else{
      (q.answers=q.answers||[]).forEach(function(an,ni){
        inner+='<div class="ansblk" style="border-left:2px solid '+(an.correct?'var(--border-success)':'var(--border-danger)')+';border-radius:0;padding-left:8px;margin:6px 0">'
          +fld('Antwort '+(ni+1)+' — korrekt: <input type="checkbox" data-an="'+ni+'" '+(an.correct?'checked':'')+' style="width:auto">',rich(an.text))
          +fld('Feedback',rich(an.feedback))
          +'<button class="mini" data-delan="'+ni+'" aria-label="Antwort löschen">'+icon('trash')+' Antwort</button></div>';});
      inner+='<button data-addan="1">'+icon('plus')+' Antwort</button> ';
    }
    inner+='<button class="mini" data-delq="'+qi+'" aria-label="Frage löschen">'+icon('trash')+' Frage</button>';
    qd.innerHTML=inner;el.appendChild(qd);
    const rs=qd.querySelectorAll(':scope > .fld .rich');
    rs[0].addEventListener('input',function(){q.questiontext=serializeRich(this);setDirty(true);});
    rs[1].addEventListener('input',function(){q.generalfeedback=serializeRich(this);setDirty(true);});
    if(q.type==='truefalse'){
      qd.querySelector('[data-q=correct]').addEventListener('change',function(){q.correct=this.value==='true';setDirty(true);});
      rs[2].addEventListener('input',function(){q.feedbackcorrect=serializeRich(this);setDirty(true);});
      rs[3].addEventListener('input',function(){q.feedbackwrong=serializeRich(this);setDirty(true);});
    }else{
      bind(qd,'.ansblk',function(block,ni){
        const an=q.answers[ni];if(!an)return;
        bindRich(block,0,function(v){an.text=v;});
        bindRich(block,1,function(v){an.feedback=v;});
        block.querySelector('[data-an]').addEventListener('change',function(){an.correct=this.checked;setDirty(true);});
        block.querySelector('[data-delan]').addEventListener('click',function(){q.answers.splice(ni,1);setDirty(true);render();});
      });
      const addBtn=qd.querySelector('[data-addan]');
      if(addBtn)addBtn.addEventListener('click',function(){q.answers.push({text:'',correct:false,feedback:''});setDirty(true);render();});
    }
    qd.querySelector('[data-delq]').addEventListener('click',function(){a.questions.splice(qi,1);setDirty(true);render();});
  });
  const foot=document.createElement('div');
  foot.innerHTML='<button data-newq="multichoice">'+icon('plus')+' Multiple-Choice</button> <button data-newq="truefalse">'+icon('plus')+' Wahr/Falsch</button>'
    +fld('Gesamtfeedback (overallfeedback, JSON)',ta(JSON.stringify(a.overallfeedback||[]),2));
  el.appendChild(foot);
  bind(foot,'[data-newq]',function(b){b.addEventListener('click',function(){
    a.questions.push(b.dataset.newq==='truefalse'
      ?{type:'truefalse',questiontext:'<p></p>',correct:true,generalfeedback:'',feedbackcorrect:'',feedbackwrong:''}
      :{type:'multichoice',questiontext:'<p></p>',generalfeedback:'',answers:[{text:'',correct:true,feedback:''}]});
    setDirty(true);render();});});
  foot.querySelector('textarea').addEventListener('input',function(){
    try{a.overallfeedback=JSON.parse(this.value);this.style.borderColor='';setDirty(true);}
    catch(err){this.style.borderColor='var(--border-danger)';}});
}
function edAssign(a,el){
  el.insertAdjacentHTML('beforeend',fld('Max. Punkte','<input type="number" value="'+(a.grade||100)+'" data-f="grade">'));
  el.querySelector('[data-f=grade]').addEventListener('input',function(){a.grade=+this.value;setDirty(true);});
}
function edGlossary(a,el){
  (a.entries=a.entries||[]).forEach(function(en,ei){
    const d=document.createElement('div');
    d.innerHTML=fld('Begriff','<input value="'+esc(en.concept)+'" style="width:100%;box-sizing:border-box">')
      +fld('Definition',rich(en.definition))
      +'<button class="mini" aria-label="Begriff löschen">'+icon('trash')+'</button>';
    d.querySelector('input').addEventListener('input',function(){en.concept=this.value;setDirty(true);});
    bindRich(d,0,function(v){en.definition=v;});
    d.querySelector('button').addEventListener('click',function(){a.entries.splice(ei,1);setDirty(true);render();});
    el.appendChild(d);});
  const b=document.createElement('button');b.innerHTML=icon('plus')+' Begriff';
  b.addEventListener('click',function(){a.entries.push({concept:'',definition:''});setDirty(true);render();});
  el.appendChild(b);
}
function edChoice(a,el){
  el.insertAdjacentHTML('beforeend',fld('Optionen (eine pro Zeile)',ta((a.options||[]).join('\n'),3)));
  el.lastElementChild.querySelector('textarea').addEventListener('input',function(){a.options=this.value.split('\n').filter(Boolean);setDirty(true);});
}
function edBook(a,el){
  (a.chapters=a.chapters||[]).forEach(function(ch,ci){
    const d=document.createElement('div');
    d.innerHTML=fld('Kapitel '+(ci+1),'<input value="'+esc(ch.title)+'" style="width:100%;box-sizing:border-box">')
      +fld('Inhalt',rich(ch.content))
      +'<button class="mini" aria-label="Kapitel löschen">'+icon('trash')+'</button>';
    d.querySelector('input').addEventListener('input',function(){ch.title=this.value;setDirty(true);});
    bindRich(d,0,function(v){ch.content=v;});
    d.querySelector('button').addEventListener('click',function(){a.chapters.splice(ci,1);setDirty(true);render();});
    el.appendChild(d);});
  const b=document.createElement('button');b.innerHTML=icon('plus')+' Kapitel';
  b.addEventListener('click',function(){a.chapters.push({title:'',content:'<p></p>'});setDirty(true);render();});
  el.appendChild(b);
}
function edFeedback(a,el){
  el.insertAdjacentHTML('beforeend',fld('Items (JSON — v1-Vereinfachung)',ta(JSON.stringify(a.items||[],null,1),6)));
  el.lastElementChild.querySelector('textarea').addEventListener('input',function(){
    try{a.items=JSON.parse(this.value);this.style.borderColor='';setDirty(true);}
    catch(err){this.style.borderColor='var(--border-danger)';}});
}
function simpleField(a,el,key,label){
  el.insertAdjacentHTML('beforeend',fld(label,'<input value="'+esc(a[key]||'')+'" style="width:100%;box-sizing:border-box">'));
  el.lastElementChild.querySelector('input').addEventListener('input',function(){a[key]=this.value;setDirty(true);});
}
function renderEditor(si,ai,el){
  const a=secs()[si].activities[ai];el.innerHTML='';
  el.insertAdjacentHTML('beforeend',fld('Name','<input value="'+esc(a.name)+'" data-f="name" style="width:100%;box-sizing:border-box">'));
  el.querySelector('[data-f=name]').addEventListener('input',function(){a.name=this.value;setDirty(true);});
  if(a.type!=='page'){
    el.insertAdjacentHTML('beforeend',fld('Beschreibung / Intro',rich(a.intro)));
    el.lastElementChild.querySelector('.rich').addEventListener('input',function(){a.intro=serializeRich(this);setDirty(true);});
  }
  if(a.type==='page')edPage(a,el);
  else if(a.type==='quiz')edQuiz(a,el);
  else if(a.type==='assign')edAssign(a,el);
  else if(a.type==='glossary')edGlossary(a,el);
  else if(a.type==='choice')edChoice(a,el);
  else if(a.type==='book')edBook(a,el);
  else if(a.type==='feedback')edFeedback(a,el);
  else if(a.type==='url')simpleField(a,el,'externalurl','Externe URL');
  else if(a.type==='resource')simpleField(a,el,'file','Dateipfad');
  else if(a.type==='folder'){
    el.insertAdjacentHTML('beforeend',fld('Dateipfade (einer pro Zeile)',ta((a.files||[]).join('\n'),3)));
    el.lastElementChild.querySelector('textarea').addEventListener('input',function(){a.files=this.value.split('\n').filter(Boolean);setDirty(true);});
  }
  else if(a.type==='forum')simpleField(a,el,'forumtype','Forumtyp (general/news/qanda/eachuser/single)');
  renderAiRow(a,el,si,ai);
}
const AI_PRESETS={
  page:[["pencil","Neu schreiben","Schreibe den Inhalt dieser Seite komplett neu: gleiche Kernaussagen, bessere Didaktik."],
        ["cut","Kürzen","Kürze den Inhalt dieser Seite auf das Wesentliche (ca. 60% der Länge)."],
        ["wand","Vereinfachen","Vereinfache die Sprache dieser Seite auf A2/B1-Niveau, kurze Sätze."],
        ["pin","Merke-Box ergänzen","Ergänze am Ende eine prägnante Merke-Box mit den 3 wichtigsten Punkten."],
        ["photo","Diagramm neu generieren","Erzeuge das eingebettete SVG-Diagramm dieser Seite neu (klarer, korrekt beschriftet, deutsch)."]],
  quiz:[["plus","Frage ergänzen","Ergänze eine weitere lernzielorientierte Frage mit vollständigem formativem Feedback."],
        ["target","Distraktoren verbessern","Verbessere die falschen Antwortoptionen: plausible, auf echten Fehlvorstellungen basierende Distraktoren."],
        ["message","Feedback schreiben","Schreibe für jede Antwort dieser Fragen ein kurzes, erklärendes Feedback."]],
  assign:[["target","Auftrag schärfen","Schärfe den Arbeitsauftrag: konkrete Schritte, messbares Handlungsprodukt, klare Abgabe."],
          ["chart-bar","Rubrik generieren","Erstelle eine transparente Bewertungsrubrik (Kriterien mal Niveaus) und füge sie dem Auftragstext hinzu."]],
  glossary:[["plus","Begriffe ergänzen","Ergänze 5 weitere zentrale Fachbegriffe dieses Kurses mit lernendengerechten Definitionen."]]};
function renderAiRow(a,el,si,ai){
  const row=document.createElement('div');row.className='ai-row';
  (AI_PRESETS[a.type]||[]).forEach(function(p){
    const b=document.createElement('button');b.innerHTML=icon(p[0])+' '+p[1]+' ↗';
    b.addEventListener('click',function(){send('ai_assist',{target:{section:si,activity:ai},instruction:p[2]});});
    row.appendChild(b);});
  const inp=document.createElement('input');inp.placeholder='Eigener KI-Auftrag für diesen Baustein';inp.style.flex='1';inp.style.minWidth='170px';
  const go=document.createElement('button');go.innerHTML=icon('robot')+' Ausführen ↗';
  go.addEventListener('click',function(){if(inp.value.trim())send('ai_assist',{target:{section:si,activity:ai},instruction:inp.value.trim()});});
  row.appendChild(inp);row.appendChild(go);el.appendChild(row);
}
render();
return {send:send,addSection:addSection};
})();
</script>"""


def main():
    ap = argparse.ArgumentParser(description="Kurs-Editor-Widget aus course.json erzeugen")
    ap.add_argument("course_json")
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    spec = json.load(open(args.course_json, encoding="utf-8"))
    out_path = args.output or (os.path.splitext(args.course_json)[0] + "_editor.html")
    html_out = build_widget(spec)
    open(out_path, "w", encoding="utf-8").write(html_out)
    print(f"Editor-Widget geschrieben: {out_path} ({len(html_out)} Zeichen)")


if __name__ == "__main__":
    main()
