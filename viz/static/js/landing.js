(function(){
  const I18N = {
    es:{
      "nav.how":"Cómo funciona","nav.results":"Resultados","nav.team":"Equipo","nav.cta":"Explorar el visor",
      "hero.eyebrow":"IA para toxicología de agroquímicos",
      "hero.title":"Detectamos químicos peligrosos antes de que el mundo los catalogue como tales.",
      "hero.sub":"Predicción de toxicidad de agroquímicos con redes neuronales de grafos e inteligencia artificial explicable.",
      "hero.cta1":"Explorar el visor","hero.cta2":"Ver cómo funciona","hero.uni":"Universidad Tecnológica de Panamá",
      "hero.scroll":"Desplazá para descubrir","hero.tag":"grafo molecular · en vivo",
      "problem.eyebrow":"El problema","problem.title":"En los campos de Panamá, no todo lo que protege es inofensivo.",
      "problem.body":"La agricultura de exportación depende de cientos de plaguicidas. Evaluar su toxicidad en laboratorio es caro y lento, y muchos se usan sin un perfil de riesgo completo.",
      "problem.f1t":"Cientos en uso","problem.f1b":"Muchos ingredientes activos circulan en el mercado agrícola.",
      "problem.f2t":"Caro y lento","problem.f2b":"Un ensayo de laboratorio toma meses y miles de dólares.",
      "problem.f3t":"Sin perfil completo","problem.f3b":"Buena parte se usa sin conocer todos sus riesgos.",
      "problem.imgph":"[ imagen: agricultura panameña ]","problem.cap":"placeholder — reemplazar por foto real",
      "idea.eyebrow":"La idea","idea.text":"Una IA que identifica y alerta sobre <span class='u'>químicos peligrosos</span> — antes de que siquiera se cataloguen como tales.",
      "risk.hi":"Alto","risk.mod":"Moderado","risk.lo":"Bajo",
      "how.eyebrow":"Cómo funciona","how.title":"De la molécula al veredicto, en cuatro pasos.",
      "how.s1t":"La molécula","how.s1b":"Partimos de su estructura química.",
      "how.s2t":"Se vuelve una red","how.s2b":"Cada átomo es un punto; cada enlace, una conexión.",
      "how.s3t":"La IA la analiza","how.s3b":"El modelo estudia cómo se conectan las partes.",
      "how.s4t":"El veredicto","how.s4b":"Un semáforo de riesgo en 12 vías de toxicidad.",
      "how.replay":"Reproducir","how.play":"Reproducir","how.pause":"Pausar",
      "how.scrub":"Arrastrá el slider o tocá un paso para explorarlo",
      "how.anaL":"Reconocés a una persona por <b>cómo se conectan</b> sus rasgos.",
      "how.anaR":"La IA reconoce el peligro por <b>cómo se conectan</b> los átomos.",
      "results.eyebrow":"Resultados","results.title":"Rigor científico, en números.",
      "results.k1":"AUC-ROC","results.k1n":"Validación cruzada 5-fold · acierta ~8 de cada 10 veces al distinguir tóxico de no tóxico.",
      "results.k2":"agroquímicos analizados","results.k2n":"Corpus del registro panameño y familias químicas.",
      "results.k3":"supera a métodos clásicos","results.k3n":"Mejor que Random Forest, MLP y SMILES2vec.",
      "results.dist":"Distribución de riesgo del corpus","results.cmp":"AUC-ROC vs. otros modelos",
      "cases.eyebrow":"Casos de estudio","cases.title":"Probalo con químicos reales.",
      "cases.fam1":"Herbicida · triazina","cases.fam2":"Herbicida · fosfonato",
      "cases.desc1":"Herbicida de amplio uso, señalado como disruptor endocrino.",
      "cases.desc2":"El herbicida más vendido del mundo, en debate por su seguridad.",
      "cases.go":"Analizar en el visor",
      "cases.drag":"Arrastrá para rotar · scroll para zoom",
      "cases.loading":"Cargando molécula…",
      "xai.eyebrow":"No es una caja negra","xai.title":"El modelo muestra su razonamiento.",
      "xai.body":"Para cada predicción resalta qué parte de la molécula la hace peligrosa — de modo que un experto puede verificar el porqué, no solo el resultado.",
      "xai.cap":"Importancia por átomo",
      "xai.taskLabel":"Diana biológica",
      "xai.loading":"Calculando importancia…",
      "xai.fallback":"Modo demo (modelo no disponible) — colores ilustrativos",
      "team.eyebrow":"Equipo","team.title":"Quiénes lo hacen.",
      "final.title":"Explorá el sistema vos mismo.","final.body":"Buscá un plaguicida, dibujá una molécula, y mirá cómo la IA la evalúa en vivo.","final.cta":"Abrir el visor",
      "footer.note":"Prototipo de diseño — contenido y cifras sujetos a verificación.",
      "lights":"Entrando al visor (tema oscuro)…"
    },
    en:{
      "nav.how":"How it works","nav.results":"Results","nav.team":"Team","nav.cta":"Open the viewer",
      "hero.eyebrow":"AI for agrochemical toxicology",
      "hero.title":"We flag dangerous chemicals before the world catalogs them as such.",
      "hero.sub":"Predicting agrochemical toxicity with graph neural networks and explainable AI.",
      "hero.cta1":"Open the viewer","hero.cta2":"See how it works","hero.uni":"Technological University of Panama",
      "hero.scroll":"Scroll to explore","hero.tag":"molecular graph · live",
      "problem.eyebrow":"The problem","problem.title":"In Panama's fields, not everything that protects is harmless.",
      "problem.body":"Export agriculture relies on hundreds of pesticides. Testing their toxicity in a lab is slow and costly, and many are used without a complete risk profile.",
      "problem.f1t":"Hundreds in use","problem.f1b":"Many active ingredients circulate in the agricultural market.",
      "problem.f2t":"Slow and costly","problem.f2b":"A lab assay takes months and thousands of dollars.",
      "problem.f3t":"No full profile","problem.f3b":"A large share is used without knowing all its risks.",
      "problem.imgph":"[ image: Panamanian agriculture ]","problem.cap":"placeholder — replace with real photo",
      "idea.eyebrow":"The idea","idea.text":"An AI that identifies and warns about <span class='u'>dangerous chemicals</span> — before they are even cataloged as such.",
      "risk.hi":"High","risk.mod":"Moderate","risk.lo":"Low",
      "how.eyebrow":"How it works","how.title":"From molecule to verdict, in four steps.",
      "how.s1t":"The molecule","how.s1b":"We start from its chemical structure.",
      "how.s2t":"It becomes a network","how.s2b":"Each atom is a point; each bond, a connection.",
      "how.s3t":"The AI analyzes it","how.s3b":"The model studies how the parts connect.",
      "how.s4t":"The verdict","how.s4b":"A risk signal across 12 toxicity pathways.",
      "how.replay":"Play","how.play":"Play","how.pause":"Pause",
      "how.scrub":"Drag the slider or tap a step to explore it",
      "how.anaL":"You recognize a person by <b>how their features connect</b>.",
      "how.anaR":"The AI recognizes danger by <b>how the atoms connect</b>.",
      "results.eyebrow":"Results","results.title":"Scientific rigor, in numbers.",
      "results.k1":"AUC-ROC","results.k1n":"5-fold cross-validation · right ~8 out of 10 times telling toxic from non-toxic.",
      "results.k2":"agrochemicals analyzed","results.k2n":"Corpus from the Panamanian registry and chemical families.",
      "results.k3":"beats classical methods","results.k3n":"Better than Random Forest, MLP and SMILES2vec.",
      "results.dist":"Risk distribution of the corpus","results.cmp":"AUC-ROC vs. other models",
      "cases.eyebrow":"Case studies","cases.title":"Try it with real chemicals.",
      "cases.fam1":"Herbicide · triazine","cases.fam2":"Herbicide · phosphonate",
      "cases.desc1":"A widely used herbicide, flagged as an endocrine disruptor.",
      "cases.desc2":"The world's best-selling herbicide, debated for its safety.",
      "cases.go":"Analyze in the viewer",
      "cases.drag":"Drag to rotate · scroll to zoom",
      "cases.loading":"Loading molecule…",
      "xai.eyebrow":"Not a black box","xai.title":"The model shows its reasoning.",
      "xai.body":"For every prediction it highlights which part of the molecule makes it dangerous — so an expert can verify the why, not just the result.",
      "xai.cap":"Per-atom importance",
      "xai.taskLabel":"Biological target",
      "xai.loading":"Computing importance…",
      "xai.fallback":"Demo mode (model unavailable) — illustrative colors",
      "team.eyebrow":"Team","team.title":"Who's behind it.",
      "final.title":"Explore the system yourself.","final.body":"Search for a pesticide, draw a molecule, and watch the AI evaluate it live.","final.cta":"Open the viewer",
      "footer.note":"Design prototype — content and figures pending verification.",
      "lights":"Entering the viewer (dark theme)…"
    }
  };
  let lang="es";
  function applyLang(l){
    lang=l; document.documentElement.setAttribute("lang",l);
    document.querySelectorAll("[data-i18n]").forEach(el=>{
      const k=el.getAttribute("data-i18n"); const v=I18N[l][k];
      if(v!=null) el.innerHTML=v;
    });
    document.querySelectorAll(".lang button").forEach(b=>b.classList.toggle("on",b.dataset.lang===l));
  }
  document.querySelectorAll(".lang button").forEach(b=>b.addEventListener("click",()=>applyLang(b.dataset.lang)));

  // theme handled by theme.js; refresh live graph on toggle
  document.addEventListener("gnntox-theme", () => {
    if (window.__refreshGraph) window.__refreshGraph();
  });

  // nav scrolled
  const nav=document.getElementById("nav");
  addEventListener("scroll",()=>nav.classList.toggle("scrolled",scrollY>20),{passive:true});

  const reduce=matchMedia("(prefers-reduced-motion:reduce)").matches;

  // reveal
  const io=new IntersectionObserver((es)=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add("in");io.unobserve(e.target);}}),{threshold:.15});
  document.querySelectorAll(".reveal").forEach(el=>io.observe(el));

  // counters
  function count(el){
    const to=parseFloat(el.dataset.count), dec=parseInt(el.dataset.dec||"0");
    if(reduce){el.textContent=to.toFixed(dec);return;}
    let s=null;const dur=1400;
    function step(t){if(!s)s=t;const p=Math.min((t-s)/dur,1);const e=1-Math.pow(1-p,3);
      el.textContent=(to*e).toFixed(dec);if(p<1)requestAnimationFrame(step);else el.textContent=to.toFixed(dec);}
    requestAnimationFrame(step);
  }
  const cio=new IntersectionObserver((es)=>es.forEach(e=>{if(e.isIntersecting){count(e.target);cio.unobserve(e.target);}}),{threshold:.6});
  document.querySelectorAll("[data-count]").forEach(el=>cio.observe(el));

  // bars (dist + comparison)
  const bio=new IntersectionObserver((es)=>es.forEach(e=>{if(e.isIntersecting){
    e.target.querySelectorAll("[data-w]").forEach(x=>x.style.width=x.dataset.w+"%");bio.unobserve(e.target);}}),{threshold:.4});
  document.querySelectorAll("#distBar,.cmp,.card").forEach(el=>bio.observe(el));

  // semaphore in idea
  const sio=new IntersectionObserver((es)=>es.forEach(e=>{if(e.isIntersecting){
    const ss=e.target.querySelectorAll(".s");ss.forEach((s,i)=>setTimeout(()=>s.classList.add("lit"),reduce?0:i*380));sio.unobserve(e.target);}}),{threshold:.5});
  const semaIdea=document.getElementById("semaIdea"); if(semaIdea)sio.observe(semaIdea);

  // pipeline — continuous progress bar; cards unlock when thumb reaches each mark
  const steps=[...document.querySelectorAll("#pipe .step")];
  const slider=document.getElementById("pipeSlider");
  const scrubFill=document.getElementById("scrubFill");
  const playBtn=document.getElementById("pipePlay");
  const nSteps=Math.max(steps.length,1);
  const maxIdx=nSteps-1;
  let pipeRun=null;
  let pipePlaying=false;
  let pipeProgress=0; // 0..1 continuous

  function progressToStep(p){
    if(p>=1)return maxIdx;
    // Unlock step i only when progress reaches mark i (0, 1/3, 2/3, 1)
    return Math.min(maxIdx, Math.floor(p*maxIdx+1e-6));
  }

  function setPipeProgress(p,{syncSlider=true}={}){
    pipeProgress=Math.max(0,Math.min(1,p));
    const pct=pipeProgress*100;
    if(scrubFill)scrubFill.style.width=pct+"%";
    if(syncSlider&&slider){
      slider.value=String(pct);
      slider.setAttribute("aria-valuenow",String(Math.round(pct)));
    }
    const idx=progressToStep(pipeProgress);
    steps.forEach((st,i)=>{
      st.classList.toggle("shown", i<=idx);
      st.classList.toggle("done", i<idx);
      st.classList.toggle("active", i===idx);
    });
    document.querySelectorAll(".scrub-mark").forEach((m,i)=>{
      m.classList.toggle("on", i===idx);
      m.classList.toggle("passed", i<=idx);
    });
  }

  function stopPipe(){
    pipePlaying=false;
    if(pipeRun){cancelAnimationFrame(pipeRun);pipeRun=null;}
    playBtn?.classList.remove("playing");
    playBtn?.setAttribute("aria-pressed","false");
    playBtn?.setAttribute("title", (I18N[lang]&&I18N[lang]["how.play"])||"Reproducir");
  }

  function playPipe(){
    if(reduce){setPipeProgress(1);stopPipe();return;}
    if(pipeRun)cancelAnimationFrame(pipeRun);
    pipePlaying=true;
    playBtn?.classList.add("playing");
    playBtn?.setAttribute("aria-pressed","true");
    playBtn?.setAttribute("title", (I18N[lang]&&I18N[lang]["how.pause"])||"Pausar");

    let startP=pipeProgress;
    if(startP>=0.999)startP=0;
    setPipeProgress(startP);
    const dur=7000; // ms for remaining distance scaled to full span
    const span=Math.max(1-startP,0.001);
    const t0=performance.now();
    function fr(now){
      if(!pipePlaying)return;
      const p=Math.min(1, startP+((now-t0)/dur)*span);
      setPipeProgress(p);
      if(p<1)pipeRun=requestAnimationFrame(fr);
      else stopPipe();
    }
    pipeRun=requestAnimationFrame(fr);
  }

  slider?.addEventListener("input",()=>{
    stopPipe();
    setPipeProgress(Number(slider.value)/100,{syncSlider:false});
  });

  document.querySelectorAll(".scrub-mark").forEach(m=>{
    m.addEventListener("click",()=>{
      stopPipe();
      const step=Number(m.dataset.step);
      setPipeProgress(maxIdx===0?1:step/maxIdx);
    });
  });

  playBtn?.addEventListener("click",()=>{
    if(pipePlaying)stopPipe();
    else playPipe();
  });

  setPipeProgress(0);
  if(reduce)setPipeProgress(1);

  // hero canvas — 3D molecular field (metallic spheres, drift right → left)
  const cv=document.getElementById("heroCanvas");
  if(cv){
    const heroEl=cv.closest(".hero")||cv.parentElement;
    const ctx=cv.getContext("2d");let W,H,dpr,raf,last=0,mols=[];
    const COL={edge:"168,178,192"};
    const NAMES=["Atrazina","Glifosato","Clorpirifos","Paraquat","Tebuconazol",
      "Cipermetrina","Malatión","2,4-D","Simazina","Deltametrina","Carbaril","Dimetoato"];
    let nameIdx=0;
    const mouse={x:-1e9,y:-1e9};
    let hoverMol=null;

    const tip=document.createElement("div");
    tip.className="mol-tip";
    tip.setAttribute("aria-hidden","true");
    heroEl.appendChild(tip);

    function readColors(){
      const cs=getComputedStyle(cv);
      COL.edge=(cs.getPropertyValue("--graph-edge-rgb").trim())||COL.edge;
    }
    function size(){dpr=Math.min(devicePixelRatio||1,2);const r=cv.getBoundingClientRect();
      W=r.width;H=r.height;cv.width=W*dpr;cv.height=H*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);}

    // molecule templates: local atom coords [x,y,z] + bonds [i,j]
    const TEMPLATES=[
      (()=>{const a=[],b=[],R=.55;for(let i=0;i<6;i++){const t=i/6*6.2832;a.push([Math.cos(t)*R,Math.sin(t)*R,0]);b.push([i,(i+1)%6]);}a.push([R+.45,0,0]);b.push([0,6]);a.push([-R-.45,0,.1]);b.push([3,7]);return{a,b};})(),
      (()=>{const a=[[0,0,0]],b=[],d=.62,dirs=[[1,1,1],[-1,-1,1],[-1,1,-1],[1,-1,-1]];dirs.forEach((v,i)=>{a.push([v[0]*d,v[1]*d,v[2]*d]);b.push([0,i+1]);});return{a,b};})(),
      (()=>{const a=[],b=[];let x=-.9;for(let i=0;i<6;i++){a.push([x,(i%2?.3:-.3),(i%2?.25:-.25)]);if(i>0)b.push([i-1,i]);x+=.36;}return{a,b};})()
    ];

    function nextName(){
      const n=NAMES[nameIdx%NAMES.length];
      nameIdx++;
      return n;
    }

    function pickY(){
      // Prefer vertical slots that aren't occupied by molecules already on-screen
      for(let tries=0;tries<10;tries++){
        const y=(Math.random()*2-1)*2.15;
        const clash=mols.some(m=>m.x>-5&&m.x<5.5&&Math.abs(m.y-y)<.85);
        if(!clash) return y;
      }
      return (Math.random()*2-1)*2.15;
    }

    function newMol(){
      return {tpl:TEMPLATES[(Math.random()*TEMPLATES.length)|0],
        name:nextName(),
        x:6.5+Math.random()*2.2,
        y:pickY(),
        z:3.2+Math.random()*4.8,
        rx:Math.random()*6.28, ry:Math.random()*6.28, rz:Math.random()*6.28,
        vrx:(Math.random()-.5)*.35, vry:(Math.random()-.5)*.35, vrz:(Math.random()-.5)*.28,
        vx:-(0.38+Math.random()*.42),
        vz:(Math.random()-.5)*.06,
        s:1.15+Math.random()*.85,
        metal:Math.random(),
        _sx:0,_sy:0,_rad:0,_alpha:0,_hit:false};
    }
    function init(){
      // Fewer molecules, wide horizontal stagger → clear gaps between them
      mols=[];
      for(let i=0;i<7;i++){
        const m=newMol();
        m.x=7.2+i*3.1;
        m.y=(-1.7+i*0.55)+((i%2)?0.35:-0.35);
        mols.push(m);
      }
    }

    function rot(p,rx,ry,rz){
      let x=p[0],y=p[1],z=p[2],c,s,t1,t2;
      c=Math.cos(rx);s=Math.sin(rx);t1=y*c-z*s;t2=y*s+z*c;y=t1;z=t2;
      c=Math.cos(ry);s=Math.sin(ry);t1=x*c+z*s;t2=-x*s+z*c;x=t1;z=t2;
      c=Math.cos(rz);s=Math.sin(rz);t1=x*c-y*s;t2=x*s+y*c;x=t1;y=t2;
      return[x,y,z];
    }

    function drawMetalSphere(sx,sy,rad,alpha,variant){
      const a=Math.min(1,alpha*1.1);
      const cool=variant>.5;
      const hx=sx-rad*.32, hy=sy-rad*.36;
      // Matte brushed metal — soft highlight, muted midtones
      const g=ctx.createRadialGradient(hx,hy,rad*.08, sx+rad*.1,sy+rad*.15,rad);
      g.addColorStop(0,`rgba(170,180,195,${a})`);
      g.addColorStop(.22,cool?`rgba(120,132,148,${a})`:`rgba(132,142,156,${a})`);
      g.addColorStop(.5,cool?`rgba(78,90,108,${a})`:`rgba(88,98,114,${a})`);
      g.addColorStop(.78,cool?`rgba(40,50,64,${a})`:`rgba(48,56,70,${a})`);
      g.addColorStop(1,`rgba(12,16,24,${a})`);
      ctx.globalAlpha=1;
      ctx.fillStyle=g;
      ctx.beginPath();ctx.arc(sx,sy,rad,0,6.2832);ctx.fill();
      const rim=ctx.createRadialGradient(sx+rad*.28,sy+rad*.32,0,sx,sy,rad);
      rim.addColorStop(0,`rgba(160,175,195,${.06*a})`);
      rim.addColorStop(.45,`rgba(160,175,195,0)`);
      rim.addColorStop(1,`rgba(0,0,0,${.4*a})`);
      ctx.fillStyle=rim;
      ctx.beginPath();ctx.arc(sx,sy,rad,0,6.2832);ctx.fill();
      // small dull specular
      ctx.fillStyle=`rgba(210,218,230,${.22*a})`;
      ctx.beginPath();ctx.ellipse(hx,hy,rad*.12,rad*.08, -.4,0,6.2832);ctx.fill();
    }

    function drawMol(m,focal){
      const enterFade=Math.min(1,Math.max(0,(7.2-m.x)/1.4));
      const exitFade=Math.min(1,Math.max(0,(m.x+7.0)/1.5));
      const depthFade=Math.min(1,Math.max(0,(10-m.z)/2))*Math.min(1,Math.max(0,(m.z-1.4)/1.0));
      const alpha=enterFade*exitFade*depthFade;
      m._alpha=alpha; m._hit=false;
      if(alpha<=.02)return;
      const pts=m.tpl.a.map(p=>{
        const r=rot(p,m.rx,m.ry,m.rz);const wz=m.z+r[2]*m.s;
        if(wz<=.35)return null;
        return{sx:W/2+(m.x+r[0]*m.s)/wz*focal, sy:H/2+(m.y+r[1]*m.s)/wz*focal, wz};
      });
      let cx=0,cy=0,n=0,maxR=0;
      ctx.lineCap="round";
      for(const bd of m.tpl.b){const p=pts[bd[0]],q=pts[bd[1]];if(!p||!q)continue;
        const lw=Math.max(1.4,(focal*.032)/((p.wz+q.wz)/2));
        ctx.strokeStyle=`rgba(40,48,62,${alpha*.85})`;
        ctx.lineWidth=lw;
        ctx.beginPath();ctx.moveTo(p.sx,p.sy);ctx.lineTo(q.sx,q.sy);ctx.stroke();
        ctx.strokeStyle=`rgba(${COL.edge},${alpha*.7})`;
        ctx.lineWidth=lw*.45;
        ctx.beginPath();ctx.moveTo(p.sx,p.sy);ctx.lineTo(q.sx,q.sy);ctx.stroke();}
      pts.forEach((p,idx)=>{if(!p)return;
        const rad=Math.max(2.2,(focal*.22*m.s)/p.wz);
        drawMetalSphere(p.sx,p.sy,rad,alpha,(m.metal+idx*.17)%1);
        cx+=p.sx; cy+=p.sy; n++;
        maxR=Math.max(maxR,rad);
      });
      if(n){
        m._sx=cx/n; m._sy=cy/n;
        // hit radius = distance to farthest atom + atom size
        let reach=maxR;
        pts.forEach(p=>{if(!p)return; reach=Math.max(reach,Math.hypot(p.sx-m._sx,p.sy-m._sy)+maxR);});
        m._rad=reach*1.05;
        m._hit=alpha>.12;
      }
    }

    function updateTip(){
      let hit=null,best=1e9;
      for(const m of mols){
        if(!m._hit) continue;
        const d=Math.hypot(mouse.x-m._sx, mouse.y-m._sy);
        if(d<m._rad && d<best){best=d; hit=m;}
      }
      if(hit){
        if(hoverMol!==hit){
          tip.textContent=hit.name;
          tip.classList.remove("leaving");
          tip.classList.add("on");
          hoverMol=hit;
          // Lock label side once, from cursor at hover start — then it only rides with the molecule
          const dx=mouse.x-hit._sx, dy=mouse.y-hit._sy;
          hit._labelAng=(dx||dy)?Math.atan2(dy,dx):-Math.PI/4;
        }
        tip.style.left=(hit._sx+Math.cos(hit._labelAng)*hit._rad*.62)+"px";
        tip.style.top=(hit._sy+Math.sin(hit._labelAng)*hit._rad*.62)+"px";
        heroEl.style.cursor="pointer";
      }else if(hoverMol){
        tip.classList.add("leaving");
        tip.classList.remove("on");
        hoverMol=null;
        heroEl.style.cursor="";
        clearTimeout(tip._t);
        tip._t=setTimeout(()=>{ if(!hoverMol) tip.textContent=""; },1200);
      }
    }

    function draw(dt){
      const focal=Math.min(W,H)*.95;
      ctx.clearRect(0,0,W,H);
      mols.sort((a,b)=>b.z-a.z);
      for(const m of mols){
        if(dt>0){
          m.x+=m.vx*dt; m.z+=m.vz*dt;
          m.rx+=m.vrx*dt; m.ry+=m.vry*dt; m.rz+=m.vrz*dt;
          if(m.x<-7.2){
            const wasHover=hoverMol===m;
            Object.assign(m,newMol());
            if(wasHover){ tip.classList.remove("on"); tip.classList.add("leaving"); hoverMol=null; }
          }
        }
        drawMol(m,focal);
      }
      updateTip();
    }
    function loop(t){const dt=last?Math.min(.05,(t-last)/1000):0;last=t;draw(dt);raf=requestAnimationFrame(loop);}
    function onMove(e){
      const r=cv.getBoundingClientRect();
      mouse.x=e.clientX-r.left; mouse.y=e.clientY-r.top;
    }
    function onLeave(){
      mouse.x=-1e9; mouse.y=-1e9;
      if(hoverMol){
        tip.classList.add("leaving"); tip.classList.remove("on"); hoverMol=null;
        heroEl.style.cursor="";
      }
    }
    function start(){readColors();size();init();cancelAnimationFrame(raf);last=0;if(reduce)draw(0);else raf=requestAnimationFrame(loop);}
    addEventListener("resize",size);
    heroEl.addEventListener("mousemove",onMove,{passive:true});
    heroEl.addEventListener("mouseleave",onLeave);
    window.__refreshGraph=()=>{readColors();if(reduce)draw(0);};
    start();
  }

  // interactive case molecules (3Dmol — CPK colors + element symbols + drag rotate)
  (function initCaseMols(){
    const lib=window.$3Dmol||window["3Dmol"];
    const nodes=[...document.querySelectorAll(".mol-live[data-smiles]")];
    if(!nodes.length)return;

    function cssColorToHex(css){
      const c=(css||"").trim();
      if(/^#([0-9a-f]{6})$/i.test(c))return "0x"+c.slice(1);
      const m=c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
      if(m){
        const h=(n)=>Number(n).toString(16).padStart(2,"0");
        return "0x"+h(m[1])+h(m[2])+h(m[3]);
      }
      return "0xf6f8fb";
    }

    function labelColorForElem(el){
      // dark text on light atoms (H, C-ish), white on saturated CPK colors
      return (el==="H"||el==="S"||el==="F"||el==="Cl"||el==="Br"||el==="I") ? "#1a1a1a" : "#ffffff";
    }

    async function mount(el){
      const smiles=el.dataset.smiles;
      const loading=el.querySelector(".mol-live-loading");
      if(!lib||typeof lib.createViewer!=="function"){
        el.classList.add("error");
        if(loading)loading.textContent="3Dmol no disponible";
        return;
      }
      try{
        const res=await fetch("/api/mol3d?smiles="+encodeURIComponent(smiles));
        if(!res.ok)throw new Error("mol3d "+res.status);
        const data=await res.json();
        const block=data.sdf||data.mol_block;
        if(!block)throw new Error("sin estructura");

        const bg=cssColorToHex(getComputedStyle(document.documentElement).getPropertyValue("--ground"));
        // clear loading text node but keep viewer target
        el.innerHTML="";
        el.classList.add("ready");
        const viewer=lib.createViewer(el,{
          backgroundColor:bg,
          antialias:true,
          disableFog:true
        });
        const fmt=data.sdf?"sdf":"mol";
        viewer.addModel(block,fmt);
        viewer.setStyle({},{
          stick:{colorscheme:"Jmol",radius:0.18},
          sphere:{colorscheme:"Jmol",scale:0.32}
        });

        const CPK={H:"#f0f0f0",C:"#909090",N:"#3050F8",O:"#FF0D0D",Cl:"#1FF01F",P:"#FF8000",S:"#FFFF30",F:"#90E050",Br:"#A62929"};
        const atoms=viewer.getModel().selectedAtoms({});
        atoms.forEach(atom=>{
          const sym=atom.elem||atom.atom||"?";
          viewer.addLabel(sym,{
            position:atom,
            fontSize:12,
            fontColor:labelColorForElem(sym),
            fontOpacity:1,
            borderThickness:0,
            backgroundColor:CPK[sym]||"#555555",
            backgroundOpacity:0.72,
            inFront:true,
            showBackground:true
          });
        });

        viewer.zoomTo();
        viewer.zoom(1.08,0);
        viewer.render();
        el._viewer=viewer;

        // keep canvas sized on resize
        const ro=new ResizeObserver(()=>{
          try{viewer.resize();viewer.render();}catch(e){}
        });
        ro.observe(el);
      }catch(err){
        console.warn("case mol",err);
        el.classList.add("error");
        el.classList.remove("ready");
        el.innerHTML=`<span class="mol-live-loading">${(I18N[lang]&&I18N[lang]["cases.loading"])||"Error al cargar"}</span>`;
        if(el.querySelector(".mol-live-loading"))
          el.querySelector(".mol-live-loading").textContent="No se pudo cargar la molécula";
      }
    }

    // lazy-load when section enters view
    const io=new IntersectionObserver((entries)=>{
      entries.forEach(en=>{
        if(!en.isIntersecting)return;
        const el=en.target;
        io.unobserve(el);
        mount(el);
      });
    },{threshold:0.2});
    nodes.forEach(n=>io.observe(n));

    // refresh background if theme toggles
    document.getElementById("themeBtn")?.addEventListener("click",()=>{
      setTimeout(()=>{
        nodes.forEach(el=>{
          if(!el._viewer)return;
          const bg=cssColorToHex(getComputedStyle(document.documentElement).getPropertyValue("--ground"));
          try{el._viewer.setBackgroundColor(bg);el._viewer.render();}catch(e){}
        });
      },50);
    });
  })();

  // XAI demo — 3D molecule colored by per-atom importance + task combobox
  (function initXaiDemo(){
    const el=document.getElementById("xaiMol");
    const sel=document.getElementById("xaiTask"); // hidden input
    const combo=document.getElementById("xaiCombo");
    const comboBtn=document.getElementById("xaiTaskBtn");
    const comboList=document.getElementById("xaiTaskList");
    const comboValue=document.getElementById("xaiTaskValue");
    const descEl=document.getElementById("xaiTaskDesc");
    const statusEl=document.getElementById("xaiStatus");
    if(!el||!sel||!combo||!comboBtn||!comboList)return;

    const lib=window.$3Dmol||window["3Dmol"];
    const SMILES=el.dataset.smiles||"CCNc1nc(Cl)nc(NC(C)C)n1";
    const TASK_DESC={
      "NR-AR":{es:"Receptor de andrógenos",en:"Androgen receptor"},
      "NR-AR-LBD":{es:"Dominio ligando AR",en:"AR ligand domain"},
      "NR-AhR":{es:"Receptor aril-hidrocarburo",en:"Aryl hydrocarbon receptor"},
      "NR-Aromatase":{es:"Aromatasa (CYP19)",en:"Aromatase (CYP19)"},
      "NR-ER":{es:"Receptor de estrógenos",en:"Estrogen receptor"},
      "NR-ER-LBD":{es:"Dominio ligando ER",en:"ER ligand domain"},
      "NR-PPAR-gamma":{es:"Receptor PPAR-γ",en:"PPAR-γ receptor"},
      "SR-ARE":{es:"Estrés oxidativo (Nrf2)",en:"Oxidative stress (Nrf2)"},
      "SR-AtAD5":{es:"Daño al ADN",en:"DNA damage"},
      "SR-HSE":{es:"Estrés por calor",en:"Heat shock response"},
      "SR-MMP":{es:"Membrana mitocondrial",en:"Mitochondrial membrane"},
      "SR-p53":{es:"Vía p53 (genotoxicidad)",en:"p53 pathway (genotoxicity)"},
    };
    const NEUTRAL="#888888";
    let viewer=null;
    let atomCount=0;
    let busy=false;

    function getTask(){return sel.value;}

    function setTask(task,{silent=false}={}){
      sel.value=task;
      if(comboValue)comboValue.textContent=task;
      comboList.querySelectorAll("[role=option]").forEach(li=>{
        const on=li.dataset.value===task;
        li.classList.toggle("on",on);
        li.setAttribute("aria-selected",on?"true":"false");
      });
      updateTaskDesc();
      if(!silent)loadExplain(task);
    }

    function openCombo(){
      combo.classList.add("open");
      comboList.hidden=false;
      comboBtn.setAttribute("aria-expanded","true");
      const cur=comboList.querySelector(".on")||comboList.querySelector("[role=option]");
      cur?.focus();
      // keep selected row visible in the 3-item window
      cur?.scrollIntoView({block:"nearest"});
    }
    function closeCombo(){
      combo.classList.remove("open");
      comboList.hidden=true;
      comboBtn.setAttribute("aria-expanded","false");
    }
    function toggleCombo(){
      if(combo.classList.contains("open"))closeCombo();
      else openCombo();
    }

    comboBtn.addEventListener("click",(e)=>{e.stopPropagation();toggleCombo();});
    comboList.querySelectorAll("[role=option]").forEach(li=>{
      li.addEventListener("click",(e)=>{
        e.stopPropagation();
        setTask(li.dataset.value);
        closeCombo();
        comboBtn.focus();
      });
    });
    document.addEventListener("click",(e)=>{
      if(!combo.contains(e.target))closeCombo();
    });
    comboBtn.addEventListener("keydown",(e)=>{
      if(e.key==="ArrowDown"||e.key==="Enter"||e.key===" "){
        e.preventDefault();openCombo();
      }else if(e.key==="Escape")closeCombo();
    });
    comboList.addEventListener("keydown",(e)=>{
      const opts=[...comboList.querySelectorAll("[role=option]")];
      const i=opts.indexOf(document.activeElement);
      if(e.key==="ArrowDown"){e.preventDefault();opts[Math.min(opts.length-1,i+1)]?.focus();}
      else if(e.key==="ArrowUp"){e.preventDefault();opts[Math.max(0,i-1)]?.focus();}
      else if(e.key==="Enter"||e.key===" "){
        e.preventDefault();
        if(document.activeElement?.dataset?.value){
          setTask(document.activeElement.dataset.value);
          closeCombo();comboBtn.focus();
        }
      }else if(e.key==="Escape"){closeCombo();comboBtn.focus();}
    });

    function cssColorToHex(css){
      const c=(css||"").trim();
      if(/^#([0-9a-f]{6})$/i.test(c))return "0x"+c.slice(1);
      const m=c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
      if(m){
        const h=(n)=>Number(n).toString(16).padStart(2,"0");
        return "0x"+h(m[1])+h(m[2])+h(m[3]);
      }
      return "0xf6f8fb";
    }

    function ylOrRd(t){
      const stops=[
        [1.00,1.00,0.80],[1.00,0.93,0.63],[0.996,0.85,0.46],
        [0.996,0.70,0.30],[0.992,0.55,0.24],[0.988,0.31,0.16],
        [0.89,0.10,0.11],[0.70,0.00,0.15],
      ];
      const x=Math.max(0,Math.min(1,t))*(stops.length-1);
      const i=Math.floor(x); const f=x-i;
      const a=stops[i], b=stops[Math.min(i+1,stops.length-1)];
      const r=Math.round(255*(a[0]+(b[0]-a[0])*f));
      const g=Math.round(255*(a[1]+(b[1]-a[1])*f));
      const bl=Math.round(255*(a[2]+(b[2]-a[2])*f));
      return "#"+[r,g,bl].map(v=>v.toString(16).padStart(2,"0")).join("");
    }

    function updateTaskDesc(){
      const t=getTask();
      const pack=TASK_DESC[t];
      if(descEl&&pack)descEl.textContent=pack[lang]||pack.es||t;
    }

    function setStatus(msg,show){
      if(!statusEl)return;
      if(!show||!msg){statusEl.hidden=true;statusEl.textContent="";return;}
      statusEl.hidden=false;statusEl.textContent=msg;
    }

    function applyColors(hexColors, importance){
      if(!viewer)return;
      viewer.removeAllLabels();
      viewer.setStyle({},{stick:{radius:0.12,color:NEUTRAL},sphere:{scale:0.16,color:NEUTRAL}});
      const atoms=viewer.selectedAtoms({model:0})||[];
      const n=Math.min(hexColors.length, atoms.length||atomCount);
      for(let i=0;i<n;i++){
        const hex=hexColors[i]||NEUTRAL;
        const imp=importance&&importance[i]!=null?Number(importance[i]):0;
        const serial=atoms[i]?atoms[i].serial:i+1;
        const sym=(atoms[i]&&(atoms[i].elem||atoms[i].atom))||"";
        viewer.setStyle({serial},{
          stick:{color:hex,radius:0.15},
          sphere:{color:hex,scale:0.2+imp*0.18}
        });
        if(sym){
          viewer.addLabel(sym,{
            position:atoms[i],
            fontSize:11,
            fontColor:imp>0.55?"#fff":"#1a1a1a",
            backgroundColor:hex,
            backgroundOpacity:0.75,
            borderThickness:0,
            inFront:true,
            showBackground:true
          });
        }
      }
      viewer.render();
    }

    function demoImportance(n){
      const out=new Array(n).fill(0.12);
      for(let i=0;i<n;i++)out[i]=0.15+0.75*Math.abs(Math.sin(i*1.7+getTask().length));
      const mx=Math.max(...out)||1;
      return out.map(v=>+(v/mx).toFixed(4));
    }

    async function loadExplain(task){
      if(busy||!viewer)return;
      busy=true;
      setStatus((I18N[lang]&&I18N[lang]["xai.loading"])||"…",true);
      try{
        const res=await fetch("/api/explain",{
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({smiles:SMILES,task,method:"gradcam"})
        });
        const data=await res.json().catch(()=>({}));
        if(!res.ok)throw new Error(data.detail||("HTTP "+res.status));
        const imp=data.importance||[];
        const colors=data.atom_colors||imp.map(ylOrRd);
        applyColors(colors,imp);
        setStatus("",false);
      }catch(err){
        console.warn("xai explain",err);
        const imp=demoImportance(atomCount||12);
        applyColors(imp.map(ylOrRd),imp);
        setStatus("",false);
      }finally{
        busy=false;
      }
    }

    async function mount(){
      if(!lib||typeof lib.createViewer!=="function"){
        el.classList.add("error");
        const ld=el.querySelector(".mol-live-loading");
        if(ld)ld.textContent="3Dmol no disponible";
        return;
      }
      try{
        const res=await fetch("/api/mol3d?smiles="+encodeURIComponent(SMILES));
        if(!res.ok)throw new Error("mol3d");
        const data=await res.json();
        const block=data.sdf||data.mol_block;
        if(!block)throw new Error("sin estructura");
        const bg=cssColorToHex(getComputedStyle(document.documentElement).getPropertyValue("--ground"));
        el.innerHTML="";
        el.classList.add("ready");
        viewer=lib.createViewer(el,{backgroundColor:bg,antialias:true,disableFog:true});
        viewer.addModel(block, data.sdf?"sdf":"mol");
        const atoms=viewer.selectedAtoms({model:0})||[];
        atomCount=atoms.length;
        viewer.zoomTo();
        viewer.zoom(1.05,0);
        viewer.render();
        el._viewer=viewer;
        const ro=new ResizeObserver(()=>{try{viewer.resize();viewer.render();}catch(e){}});
        ro.observe(el);
        updateTaskDesc();
        await loadExplain(getTask());
      }catch(err){
        console.warn("xai mol",err);
        el.classList.add("error");
        el.innerHTML=`<span class="mol-live-loading">No se pudo cargar la molécula</span>`;
      }
    }

    document.querySelectorAll(".lang button").forEach(b=>{
      b.addEventListener("click",()=>setTimeout(updateTaskDesc,0));
    });

    document.getElementById("themeBtn")?.addEventListener("click",()=>{
      setTimeout(()=>{
        if(!viewer)return;
        const bg=cssColorToHex(getComputedStyle(document.documentElement).getPropertyValue("--ground"));
        try{viewer.setBackgroundColor(bg);viewer.render();}catch(e){}
      },50);
    });

    const io=new IntersectionObserver((entries)=>{
      entries.forEach(en=>{
        if(!en.isIntersecting)return;
        io.unobserve(en.target);
        mount();
      });
    },{threshold:0.2});
    io.observe(el);

    // lucide chevron if icons already ran
    if(window.lucide)try{lucide.createIcons({nodes:[comboBtn]});}catch(e){}
  })();

  // lights out -> visor
  const lo=document.getElementById("lightsout");
  document.querySelectorAll(".go-visor").forEach(a=>a.addEventListener("click",(ev)=>{
    const dest=a.getAttribute("href")||"/visor";
    if(dest.startsWith("/analyze")) return;
    ev.preventDefault();
    if(reduce){window.location.href=dest;return;}
    lo.classList.add("on");
    setTimeout(()=>{window.location.href=dest;},1100);
  }));

  applyLang("es");
})();
