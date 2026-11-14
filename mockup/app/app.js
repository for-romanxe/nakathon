/* Crew Health · 공통 데이터·상태·셸·바디 엔진 · 회의 논의용 가상 데이터 */
(function(){
const KEY='crewhealth.v2';
const SOL=142;

/* ---------- 지표 메타 (E4 기반 6개) ---------- */
const META={
  hr:{l:'심박',u:'bpm',d:0,h:'안정 시',src:'E4 PPG'},
  hrv:{l:'HRV',u:'ms',d:0,h:'RMSSD · 야간',src:'E4 PPG'},
  eda:{l:'피부전기활동',u:'µS',d:1,h:'EDA · 손목',src:'E4 EDA'},
  temp:{l:'피부온',u:'°C',d:1,h:'손목',src:'E4 TEMP'},
  sleep:{l:'수면',u:'h',d:1,h:'지난밤',src:'밴드 + 자가보고'},
  act:{l:'운동',u:'min',d:0,h:'어제 · 목표 150',src:'밴드 ACC · 장비 로그'}
};
const MK=Object.keys(META);

/* ---------- 승무원 ---------- */
const CREW={
  A:{id:'A',name:'승무원 A',role:'비행 엔지니어',cmo:false,baselineDays:14,
     base:{hr:68,hrv:52,eda:1.9,temp:33.9,sleep:6.83,act:142},
     sd:{hr:9,hrv:10,eda:0.9,temp:0.35,sleep:0.7,act:16},
     now:{hr:92,hrv:31,eda:3.5,temp:34.1,sleep:5.17,act:128},
     sync:'06:10',wear:'착용 중',streak:22,mass:74.8,due:{diet:142,pmc:142,mass:142,vitals:180}},
  B:{id:'B',name:'승무원 B',role:'의료 담당(CMO) · 사령관',cmo:true,baselineDays:14,
     base:{hr:61,hrv:64,eda:1.4,temp:33.6,sleep:7.1,act:150},
     sd:{hr:7,hrv:11,eda:0.6,temp:0.3,sleep:0.6,act:12},
     now:{hr:63,hrv:61,eda:1.6,temp:33.7,sleep:6.9,act:154},
     sync:'06:02',wear:'착용 중',streak:40,mass:68.2,due:{diet:145,pmc:145,mass:150,vitals:142}},
  C:{id:'C',name:'승무원 C',role:'과학 임무',cmo:false,baselineDays:9,
     base:{hr:72,hrv:45,eda:2.2,temp:34.0,sleep:6.5,act:132},
     sd:{hr:10,hrv:12,eda:1.1,temp:0.4,sleep:0.9,act:18},
     now:{hr:74,hrv:47,eda:2.0,temp:34.0,sleep:6.7,act:138},
     sync:'06:21',wear:'착용 중',streak:8,mass:81.5,due:{diet:146,pmc:146,mass:142,vitals:148}},
  D:{id:'D',name:'승무원 D',role:'조종사',cmo:false,baselineDays:14,
     base:{hr:58,hrv:70,eda:1.2,temp:33.5,sleep:7.4,act:156},
     sd:{hr:6,hrv:12,eda:0.5,temp:0.3,sleep:0.5,act:15},
     now:{hr:71,hrv:66,eda:1.3,temp:33.9,sleep:7.2,act:160},
     sync:'05:48',wear:'충전 중 · 2h 전 분리',streak:13,mass:77.0,due:{diet:144,pmc:144,mass:152,vitals:171}}
};

/* ---------- 정기 기록 (주기는 notes/iss-crew-health-routine.md · 날짜는 가상) ---------- */
const ROUTINE={
  diet:{l:'주간 식이 설문',every:7,sub:'주 1회 · 1분',doc:'hrp:routine-01#p4'},
  pmc:{l:'주간 PMC 준비 요약',every:7,sub:'주 1회 · 확인만',doc:'hrp:routine-01#p6'},
  mass:{l:'월간 체질량',every:30,sub:'월 1회 · 질량 측정 장치',doc:'hrp:routine-01#p4'},
  vitals:{l:'분기 활력징후',every:90,sub:'분기 · 의료 담당 평가',doc:'hrp:routine-01#p5'}
};

/* ---------- 가능한 상태 목록 (기기 내 고정 · 가상 · 모델은 이 밖의 이름을 못 씀) ---------- */
const CONDS={
  orthostatic:{n:'기립성 저혈압',cat:'심혈관 적응 · 체액 이동'},
  sms:{n:'우주 멀미',cat:'감각운동 · 전정'},
  dehydration:{n:'탈수',cat:'영양 · 체액'},
  sleep_loss:{n:'수면 부족',cat:'수면 · 피로'},
  co2_headache:{n:'두통(CO2 관련)',cat:'환경(CO2) · 체액 이동'},
  msk_pain:{n:'근골격 통증',cat:'근골격'},
  uri:{n:'상기도 감염',cat:'면역 · 감염'},
  rash:{n:'피부 발진',cat:'면역 · 피부'},
  iop:{n:'안압 상승 의심',cat:'시각(SANS) · 체액 이동'},
  mood_low:{n:'불안·기분 저하',cat:'행동 건강'}
};

/* ---------- 절차서 (기기 내 문서, 가상) ---------- */
const DOCS={
  'hrp:sm-03':{t:'기립성 저혈압·어지러움 대응 절차',org:'HRP 임상 가이드 · v3.2',ps:[
    '어지러움·메스꺼움이 보고되면 먼저 기립 시 악화 여부를 확인한다. 기립 시 악화는 체액 이동과 자율신경 적응 지연을 시사한다.',
    '안정 시 심박이 개인 기준선보다 +2σ 이상이고 HRV가 -2σ 이하이면 자율신경 반응이 겹친 것으로 보고, 당일 활동을 저강도로 조정한다.',
    '수분 500 mL와 염분을 보충하고 30분 뒤 안정 시 심박을 다시 측정한다.',
    '증상이 2시간 안에 가라앉지 않거나 의식 저하·흉통이 동반되면 의료 담당에게 즉시 보고한다.',
    '당일 운동은 저강도 유산소로 제한하고, 운동 중 심박이 안정 시 +40 bpm을 넘지 않게 한다.']},
  'hrp:sleep-02':{t:'수면 부족 판정과 다음 날 조정',org:'HRP 수면 가이드 · v2.0',ps:[
    '지난밤 총 수면이 개인 기준선보다 1.5시간 이상 짧으면 수면 부족으로 본다. 깊은 수면 비율도 함께 본다.',
    '수면 부족 날에는 정밀 작업을 오전 늦게로 미루고, 카페인은 정오 이전으로 제한한다.',
    '3일 연속 부족이면 의료 담당과 수면 계획을 다시 세운다.']},
  'hrp:sm-01':{t:'일일 건강 자가 점검 항목',org:'HRP 임상 가이드 · v3.2',ps:[
    '기상 후 밴드 동기화, 체온·안정 시 심박 확인, 증상 자가 보고를 한 세트로 수행한다.',
    '모든 판정은 개인 기준선(최근 14일)과 비교한다. 기준선이 모이기 전에는 판정하지 않는다.',
    '기록은 기기 안에 남기고, 전송 창에 맞춰 지상 의료팀에 요약을 보낸다.']},
  'hrp:emer-01':{t:'흉통·호흡곤란 즉시 대응',org:'HRP 응급 절차 · v1.4',ps:[
    '흉통 또는 호흡곤란이 보고되면 모델 해석을 거치지 않고 즉시 경보한다.',
    '승무원을 앉히고 활동을 중단한다. 의료 담당을 호출한다.',
    '12유도 심전도와 산소포화도를 측정한다. 산소포화도 90% 미만이면 산소를 공급한다.',
    '지상 의료팀 긴급 큐에 측정값을 포함해 전송한다. 응답 지연은 왕복 최대 44분이다.']},
  'hrp:cv-01':{t:'심혈관 적응 모니터링 지표',org:'HRP 심혈관 가이드 · v2.3',ps:[
    '장기 임무에서는 안정 시 심박·HRV·기립 반응을 주 단위로 추적한다.',
    '기준선 재계산은 14일 창으로 하며, 이벤트가 있는 날은 제외한다.']},
  'hrp:emer-02':{t:'지표 경보 임계(±3σ) 대응',org:'HRP 응급 절차 · v1.4',ps:[
    '어떤 지표든 개인 기준선 ±3σ를 넘으면 설명 모델을 거치지 않고 규칙으로 바로 경보한다.',
    '밴드 착용 상태와 피부 접촉을 확인하고, 앉아서 5분 쉰 뒤 다시 측정한다.',
    '재측정에서도 ±3σ 밖이면 활동을 멈추고 의료 담당을 호출한다.',
    '측정값을 포함해 지상 의료팀 큐에 전송한다. 오경보로 종결하려면 이유를 기록한다.']},
  'hrp:routine-01':{t:'승무원 정기 건강 일정 요약',org:'팀 요약 · 가상 문서 (OCHMO-STD-100.1A·ISS 타임라인 참고)',ps:[
    '수면은 매일 질과 양을 기록하고, 매주 비행의와의 사적 면담(PMC)에서 함께 본다.',
    '기분·피로·스트레스는 매일 짧은 눈금으로 기록한다. 하루 입력은 5분을 넘기지 않는다.',
    '운동은 하루 약 2시간 30분이 일정에 들어 있다. 저항 운동 85–90분과 유산소 60분이며, 장비와 밴드가 시간을 자동으로 기록한다.',
    '식이는 매주 짧은 설문으로 보고, 체질량은 매월 질량 측정 장치로 잰다.',
    '분기마다 의료 담당의 건강 평가에서 활력징후(체온·혈압·맥박·호흡)를 측정한다.',
    '매주 PMC 전에 지난 7일의 수면, 기준선 밖 지표, 이벤트를 자동으로 요약해 승무원이 확인한다.']},
  'data:e4:S03':{t:'손목 EDA 해석 메모 (프록시 데이터)',org:'팀 메모 · PhysioNet E4 기반',ps:[
    'EDA 상승은 교감신경 활성(스트레스·운동·온도)과 함께 나타난다. 단독으로 판정하지 않는다.',
    '프록시 데이터는 지구의 건강한 성인 기록이다. 우주 환경 보정은 되어 있지 않다.']}
};

/* ---------- 이벤트 (시드) ---------- */
const SEED_EVENTS=[
  {id:'ev-142-01',crew:'A',sol:142,time:'06:11',title:'수면 부족 · 심박↑ · HRV↓',symptom:'(규칙 자동 생성 · 증상 입력 없음)',auto:true,codes:['rule_multi'],
   level:'caution',verified:5,runs:[
     {n:1,ok:false,fails:['numbers'],note:'수면을 5h 40m으로 서술 (실제 5h 10m) → 폐기'},
     {n:2,ok:true,fails:[]}],
   findings:[{m:'sleep',v:5.17},{m:'hr',v:92},{m:'hrv',v:31}],
   explanation:'지난밤 수면 5h 10m이 기준 6h 50m보다 1h 40m 짧고, 안정 시 심박 92 bpm은 기준선 68보다 +2.7σ, 야간 HRV 31 ms는 -2.1σ입니다. 회복이 덜 된 양상이라 오늘은 운동 강도를 낮추고 정밀 작업을 오전 늦게로 미루도록 조정했습니다 [hrp:sm-03#p2][hrp:sleep-02#p1][hrp:sleep-02#p2].',
   actions:[{t:'오늘 운동은 저강도 1시간 (심박 +40 이내)',doc:'hrp:sm-03#p5',k:'ex'},{t:'정밀 작업은 오전 늦게 · 카페인은 정오 전까지',doc:'hrp:sleep-02#p2',k:'sleep'}],
   shared:false,status:'open'},
  {id:'ev-139-01',crew:'A',sol:139,time:'21:15',title:'두통',symptom:'저녁부터 머리가 띵해요.',sym:true,codes:['headache'],
   level:'hold',verified:3,runs:[
     {n:1,ok:false,fails:['numbers','cite'],note:'기준선 수치 불일치 + 출처 없는 문장'},
     {n:2,ok:false,fails:['numbers'],note:'HRV를 기준보다 높다고 서술 (실제 -0.4σ)'}],
   findings:[{m:'hr',v:71},{m:'hrv',v:48},{m:'temp',v:34.0}],
   explanation:null,risk:{cat:'환경(CO2) · 체액 이동',cond:[],why:null,todo:'수분 섭취 후 1시간 관찰, 계속되면 의료 담당에게 보고 [hrp:sm-01#p1][hrp:sm-03#p4]'},
   actions:[{t:'수분 섭취 후 1시간 관찰',doc:'hrp:sm-01#p1'},{t:'증상 지속 시 의료 담당 보고',doc:'hrp:sm-03#p4'}],
   shared:false,status:'closed',closedNote:'Sol 140 06:00 증상 소실 · 종결'},
  {id:'ev-135-02',crew:'D',sol:135,time:'15:30',title:'운동 후 심박 회복 지연',symptom:'(규칙 자동 생성 · 증상 입력 없음)',auto:true,codes:['recovery'],
   level:'normal',verified:5,runs:[{n:1,ok:true,fails:[]}],
   findings:[{m:'hr',v:74}],
   explanation:'운동 종료 5분 뒤 심박 74 bpm은 기준선 58보다 +2.7σ 높지만, 운동 직후 측정이라 안정 시 비교가 아닙니다. 30분 뒤 측정에서 61 bpm으로 복귀했습니다 [hrp:cv-01#p1].',
   actions:[{t:'다음 운동 때 회복 5·30분 재측정',doc:'hrp:cv-01#p1'}],
   shared:true,status:'closed',closedNote:'CMO 확인 · 추적만'}
];

const CHECKS=[
  {id:'numbers',l:'숫자 일치',d:'설명 속 수치가 실제 측정값·기준선과 같다'},
  {id:'cite',l:'출처 존재',d:'모든 문장에 기기 내 문서 id가 있다'},
  {id:'level',l:'판정 일치',d:'설명이 규칙 판정보다 세게(또는 약하게) 말하지 않는다'},
  {id:'schema',l:'형식',d:'JSON 스키마·enum 밖 증상 코드 없음'},
  {id:'scope',l:'목록 밖 이름 없음 + 단정 표현 없음',d:'상태 이름은 기기 내 고정 목록(10개)에서만, 늘 "가능성"으로 말하고 "입니다" 같은 단정을 쓰지 않는다'}
];

/* ---------- 상태 저장 ---------- */
function defaults(){return {me:'A',todos:{},events:JSON.parse(JSON.stringify(SEED_EVENTS)),overrides:[],log:[
  {sol:142,time:'06:10',who:'A',text:'밴드 동기화 · 야간 데이터 7h 52m 수신'},
  {sol:142,time:'06:11',who:'A',text:'규칙: 수면 -2.4σ · 심박 +2.7σ · HRV -2.1σ · 지표 3개 → 주의 · ev-142-01'},
  {sol:142,time:'06:02',who:'B',text:'밴드 동기화 · 정상'},
  {sol:142,time:'06:21',who:'C',text:'밴드 동기화 · 기준선 9/14일'},
  {sol:142,time:'05:48',who:'D',text:'밴드 분리 · 충전 · 규칙: 심박 +2.2σ 하루 → 참고'}],
  tx:[{id:'tx-141',sol:141,time:'20:00',crew:'ALL',kind:'일일 요약',status:'전송됨',ack:'Sol 141 20:31 수신 확인'}],
  settings:{sens:'std',window:14,cmoRead:true,crewRead:false,txTime:'20:00',voice:true},
  daily:{},done:{},recheck:{},exercise:[],procViews:{}};}
let S=load();
function load(){let s=null;try{const j=JSON.parse(localStorage.getItem(KEY));if(j&&j.events)s=Object.assign(defaults(),j);}catch(e){}return s||defaults();}
function save(){try{localStorage.setItem(KEY,JSON.stringify(S));}catch(e){}}
function reset(){S=defaults();save();}

/* ---------- 계산 ---------- */
const THR={std:[2,3],low:[2.3,3.3],high:[1.8,2.6]};
function thr(){return THR[S.settings.sens]||THR.std;}
function crew(id){return CREW[id||S.me];}
function me(){return CREW[S.me];}
function z(k,c){c=c||me();return (c.now[k]-c.base[k])/c.sd[k];}
function rawLvl(k,c){c=c||me();if(c.baselineDays<14)return 'hold';const a=Math.abs(z(k,c)),t=thr();return a>=t[1]?'warning':a>=t[0]?'caution':'normal';}
function outMs(c){return MK.filter(k=>{const r=rawLvl(k,c);return r==='caution'||r==='warning';});}
function yz(k,c){return (series(k,c,7)[5]-c.base[k])/c.sd[k];}
function overridden(k,c){return S.events.some(e=>e.crew===c.id&&e.metric===k&&e.status==='closed');}
/* 경보 계층: 참고(지표 1개·하루) · 주의(이틀 연속 | 지표 2개+ | 지표+증상) · 경보(증상 규칙 | ±3σ) */
function tierInfo(c){c=c||me();if(c.baselineDays<14)return {L:'hold',why:'baseline',ms:[]};
  const o=outMs(c);const ev=S.events.find(e=>e.crew===c.id&&e.status==='open'&&e.level==='warning');
  if(ev)return {L:'warning',why:ev.metric?'sigma':'symptom',ms:o,ev};
  const w=o.filter(k=>rawLvl(k,c)==='warning'&&!overridden(k,c));if(w.length)return {L:'warning',why:'sigma',ms:w};
  if(o.length>=2)return {L:'caution',why:'multi',ms:o};
  if(o.length===1){if(Math.abs(yz(o[0],c))>=thr()[0])return {L:'caution',why:'days',ms:o};
    if(S.events.some(e=>e.crew===c.id&&e.status==='open'&&e.sym))return {L:'caution',why:'symptom',ms:o};
    return {L:'advisory',why:'one',ms:o};}
  return {L:'normal',why:'',ms:[]};}
function tier(c){return tierInfo(c).L;}
function lvl(k,c){c=c||me();const r=rawLvl(k,c);if(r==='caution'&&tier(c)==='advisory')return 'advisory';if(r==='warning'&&overridden(k,c))return 'caution';return r;}
function fmt(v,k){return k==='sleep'?`${Math.floor(v)}h ${String(Math.round((v%1)*60)).padStart(2,'0')}m`:Number(v).toFixed(META[k].d);}
function sig(v){return (v>=0?'+':'')+v.toFixed(1)+'σ';}
function series(k,c,n){c=c||me();const out=[];let seed=(c.id.charCodeAt(0)*31+k.length*7)%97;const rnd=()=>{seed=(seed*9301+49297)%233280;return seed/233280-.5;};
  for(let i=0;i<n;i++){let v=c.base[k]+rnd()*c.sd[k]*.9;if(c.id==='A'&&i>=n-3&&k!=='temp'&&k!=='eda'&&k!=='act')v=c.base[k]+(c.now[k]-c.base[k])*((i-(n-4))/3);if(i===n-1)v=c.now[k];out.push(v);}return out;}
function levelName(L){return {normal:'정상',advisory:'참고',caution:'주의',warning:'경보',hold:'보류'}[L]||L;}
function levelEn(L){return {normal:'NORMAL',advisory:'ADVISORY',caution:'CAUTION',warning:'WARNING',hold:'HOLD'}[L]||L;}
function openEvents(cid){return S.events.filter(e=>e.status==='open'&&(!cid||e.crew===cid));}
function warnEvent(){return S.events.find(e=>e.status==='open'&&e.level==='warning'&&(e.crew===S.me||me().cmo));}
function newId(){return 'ev-'+SOL+'-'+String(S.events.filter(e=>e.sol===SOL).length+1).padStart(2,'0');}
/* ±3σ는 규칙이 바로 경보 이벤트를 만든다 (모델 건너뜀). 종결(무시)된 지표는 다시 만들지 않음 */
function autoWarn(c){c=c||me();const T=tierInfo(c);if(T.L!=='warning'||T.why!=='sigma'||T.ev)return null;const k=T.ms[0];
  const e={id:newId(),crew:c.id,sol:SOL,time:hhmm(),title:`${META[k].l} ${sig(z(k,c))} · 경보 임계`,symptom:null,auto:true,metric:k,codes:['rule_3sigma'],level:'warning',verified:0,runs:[],
    findings:outMs(c).map(m=>({m,v:c.now[m]})),explanation:null,skipModel:true,doc:'hrp:emer-02',actions:DOCS['hrp:emer-02'].ps.slice(1).map((p,i)=>({t:p,doc:'hrp:emer-02#p'+(i+2)})),shared:true,status:'open'};
  S.events.unshift(e);save();addLog(`WARNING · ${META[k].l} ${sig(z(k,c))} · 규칙 ±${thr()[1]}σ · 모델 건너뜀 · ${e.id}`,c.id);return e;}

/* ---------- 체크인 · 정기 기록 ---------- */
function daily(cid){return S.daily[cid]||(S.daily[cid]={});}
function streak(c){c=c||me();return c.streak+(daily(c.id).am?1:0);}
function exToday(cid){return (S.exercise||[]).filter(x=>x.crew===cid).reduce((a,x)=>a+x.min,0);}
function routine(c,k){c=c||me();const d=(S.done[c.id]||{})[k],due=c.due[k];if(d)return {st:'done',at:d.at,next:due+ROUTINE[k].every};if(due<=SOL)return {st:'due'};return {st:'later',next:due,in:due-SOL};}
function jo(s){const ch=s.charCodeAt(s.length-1);return s+(ch>=0xAC00&&ch<=0xD7A3&&(ch-0xAC00)%28?'이':'가');}

/* ---------- 시계 ---------- */
const t0=Date.now();const b=new Date();const tq=location.search.match(/[?&]t=(\d{1,2}):(\d{2})/);b.setHours(tq?+tq[1]:7,tq?+tq[2]:5,0,0);
function now(){return new Date(b.getTime()+(Date.now()-t0));}
function clock(){const d=now();return `Sol ${SOL} · ${d.toTimeString().slice(0,5)}`;}
function hhmm(){return now().toTimeString().slice(0,5);}

/* ---------- 셸 ---------- */
const NAV=[['today','오늘','1'],['body','몸','2'],['trends','추세','3'],['log','기록','4'],['procedures','절차서','5'],['crew','승무원','6']];
function shell(active,title,crumb){
  const c=me();const T=tier(c);const w=warnEvent();
  const rail=`<nav class="rail" aria-label="주 메뉴">
    <div class="brand"><div class="lg">CH</div><div><b>Crew Health</b><small>Sol ${SOL} · 회의 논의용</small></div></div>
    ${NAV.map(([id,l,n])=>`<a href="${id}.html" class="${active===id?'on':''}"><span class="n">${n}</span>${l}${id==='today'&&T==='caution'?'<span class="bd badge caution">주의</span>':''}${id==='crew'&&c.cmo&&openEvents().length?`<span class="bd badge num">${openEvents().length}</span>`:''}${id==='crew'&&!c.cmo?'<span class="bd badge" title="의료 담당 전용">CMO</span>':''}</a>`).join('')}
    <div class="sp"></div>
    <a href="settings.html" class="${active==='settings'?'on':''}"><span class="n">⚙</span>설정</a>
    <div class="who"><div class="av">${c.id}</div><div><b>${c.name}</b><small>${c.role}</small></div></div>
    <div class="foot">가상 데이터 · 의료 조언 아님<br>모델 Qwen3-4B · 기기 내 · 오프라인</div>
  </nav>`;
  const strip=w?`<div class="wstrip"><span class="badge bd">WARNING</span><span>${CREW[w.crew].name} · ${w.title} · ${w.time}</span><a href="warning.html?id=${w.id}">경보 화면 열기</a></div>`:'';
  const top=`<header class="topbar">${crumb?`<span class="crumb">${crumb} /</span>`:''}<h1>${title}</h1><div class="sp"></div>
    <div class="meta"><span id="clock">${clock()}</span><span>동기화 ${c.sync}</span><span><i class="dot"></i>모델 대기</span></div></header>`;
  const host=document.getElementById('app');
  host.className='shell';host.innerHTML=rail+`<div class="main">${strip}${top}<main class="content ${host.dataset.wide!==undefined?'wide':''}" id="content"></main></div>`;
  setInterval(()=>{const el=document.getElementById('clock');if(el)el.textContent=clock();},1000);
  if(!document.getElementById('toast')){const t=document.createElement('div');t.id='toast';t.className='toast';document.body.appendChild(t);}
  return document.getElementById('content');
}
let toastT;function toast(msg){const el=document.getElementById('toast');if(!el)return;el.textContent=msg;el.classList.add('on');clearTimeout(toastT);toastT=setTimeout(()=>el.classList.remove('on'),2400);}
function addLog(text,who){S.log.unshift({sol:SOL,time:hhmm(),who:who||S.me,text});save();}
function q(name){return new URLSearchParams(location.search).get(name);}
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function citeLinks(text){return esc(text).replace(/\[([a-z]+:[a-z0-9-]+#p\d+)\]/g,(m,id)=>`<a class="cite" href="procedures.html?id=${encodeURIComponent(id)}">${id}</a>`);}
function citeA(id){return `<a class="cite" href="procedures.html?id=${encodeURIComponent(id)}">${id}</a>`;}

/* ---------- 타일·스파크 ---------- */
function spark(arr,base,col){const mn=Math.min(...arr,base),mx=Math.max(...arr,base);const Y=v=>30-((v-mn)/((mx-mn)||1))*26+2;const pts=arr.map((v,i)=>`${i/(arr.length-1)*100},${Y(v)}`).join(' ');const last=pts.split(' ').pop().split(',');
  return `<svg viewBox="0 0 100 34" preserveAspectRatio="none" aria-hidden="true"><line x1="0" x2="100" y1="${Y(base)}" y2="${Y(base)}" stroke="#2A3646" stroke-width="1" stroke-dasharray="2 3"/><polyline fill="none" stroke="${col}" stroke-width="1.4" points="${pts}" vector-effect="non-scaling-stroke"/><circle cx="${last[0]}" cy="${last[1]}" r="2" fill="${col}"/></svg>`;}
function tile(k,c,opts){c=c||me();opts=opts||{};const L=lvl(k,c),zz=z(k,c);const col=L==='warning'?'#FF5C73':L==='caution'?'#F5C542':'#7F8A99';const arrow=(L==='normal'||L==='hold')?'':`<span class="arrow">${zz>0?'▲':'▼'}</span>`;
  const stale=k==='sleep'?c.sync:k==='act'?'어제':'';
  const baseLine=c.baselineDays<14?`기준선 수집 중 · ${c.baselineDays}/14일`:`기준 ${fmt(c.base[k],k)} · <b>${sig(zz)}</b>${opts.sm?'':L==='warning'?' · 경보 임계':L==='caution'?' · 주의 임계':''}`;
  return `<a class="tile ${L} ${opts.lg?'lg':''} ${opts.sm?'sm':''}" href="${opts.href||('trends.html?m='+k)}" data-k="${k}">${stale?`<span class="stale">${stale}</span>`:''}<div class="k">${META[k].l}<small>${META[k].h}</small></div><div class="v">${fmt(c.now[k],k)}<small>${k==='sleep'?'':META[k].u}</small>${arrow}</div><div class="base">${baseLine}</div>${spark(series(k,c,7),c.base[k],col)}</a>`;}

/* ---------- 픽셀 바디 ---------- */
const REGIONS=[
  {id:'head',name:'머리 · 수면',cx:0.5,cy:0.09,r:0.075,ms:['sleep'],note:'수면 길이와 깊은 수면 비율을 봅니다.',doc:'hrp:sleep-02#p1'},
  {id:'heart',name:'심장 · 순환',cx:0.56,cy:0.33,r:0.09,ms:['hr','hrv'],note:'안정 시 심박과 야간 HRV. 둘이 반대로 움직이면 자율신경 반응을 의심합니다.',doc:'hrp:sm-03#p2'},
  {id:'core',name:'몸통 · 호흡/체온',cx:0.5,cy:0.44,r:0.08,ms:['temp'],note:'손목 피부온을 대리 지표로 씁니다. 심부 체온은 아닙니다.',doc:'hrp:sm-01#p1'},
  {id:'wrist',name:'왼손목 · 피부전기',cx:0.15,cy:0.535,r:0.055,ms:['eda'],note:'EDA는 스트레스·운동·온도에 함께 반응합니다. 단독 판정 안 함.',doc:'data:e4:S03#p1'},
  {id:'legs',name:'하지 · 활동',cx:0.5,cy:0.78,r:0.11,ms:['act'],note:'활동 분과 운동 중 심박 상한을 봅니다.',doc:'hrp:sm-03#p5'}
];
function rLvl(r,c){c=c||me();if(c.baselineDays<14)return 'hold';let L='normal';for(const m of r.ms){const l=lvl(m,c);if(l==='warning')return 'warning';if(l==='caution')L='caution';else if(l==='advisory'&&L==='normal')L='advisory';}return L;}
function mountBody(canvas,cid,opts){opts=opts||{};const c=CREW[cid||S.me];const bx=canvas.getContext('2d');let cells=[],cellPx=7,built='',hoverR=null;const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const PATHS=['M62 96 Q110 78 158 96 L166 200 Q160 250 150 262 L70 262 Q60 250 54 200 Z','M62 98 Q40 110 36 150 L26 236 Q24 250 34 252 L44 252 Q52 250 54 236 L64 160 Z','M158 98 Q180 110 184 150 L194 236 Q196 250 186 252 L176 252 Q168 250 166 236 L156 160 Z','M72 262 L104 262 L108 330 L104 430 Q104 444 92 444 L78 444 Q68 444 70 430 L62 330 Z','M116 262 L148 262 L158 330 L150 430 Q152 444 142 444 L128 444 Q116 444 116 430 L112 330 Z'];
  function geo(){const r=canvas.getBoundingClientRect();const W=r.width,H=r.height;const s=Math.min(W/220,H/460)*0.92;return {W,H,s,ox:(W-220*s)/2,oy:(H-460*s)/2,r};}
  function build(W,H){const off=document.createElement('canvas');off.width=W;off.height=H;const o=off.getContext('2d');const s=Math.min(W/220,H/460)*0.92,ox=(W-220*s)/2,oy=(H-460*s)/2;o.setTransform(s,0,0,s,ox,oy);o.fillStyle='#fff';
    for(const d of PATHS)o.fill(new Path2D(d));o.beginPath();o.ellipse(110,42,26,32,0,0,Math.PI*2);o.fill();o.beginPath();o.roundRect(98,72,24,18,8);o.fill();
    const d=o.getImageData(0,0,W,H).data;cells=[];cellPx=Math.max(4,Math.floor(Math.min(W,H)/(opts.dense?70:58)));let seed=7;const rnd=()=>{seed=(seed*9301+49297)%233280;return seed/233280;};
    for(let y=cellPx/2;y<H;y+=cellPx)for(let x=cellPx/2;x<W;x+=cellPx){if(d[((y|0)*W+(x|0))*4+3]>128){const nx=(x-ox)/(220*s),ny=(y-oy)/(460*s);let reg=null,best=1e9;for(const r of REGIONS){const dd=Math.hypot((nx-r.cx)*0.48,ny-r.cy);if(dd<r.r&&dd<best){best=dd;reg=r;}}cells.push({x,y,reg,light:rnd()<.08,seed:rnd(),dist:reg?best/reg.r:0});}}
    built=W+'x'+H;}
  function draw(){const g=geo();if(!g.W){requestAnimationFrame(draw);return;}const W=Math.floor(g.W),H=Math.floor(g.H);if(built!==W+'x'+H){canvas.width=W*devicePixelRatio;canvas.height=H*devicePixelRatio;build(W,H);}
    bx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0);bx.clearRect(0,0,W,H);const t=reduce?0:performance.now()/1000;const st={};for(const r of REGIONS)st[r.id]=rLvl(r,c);
    for(const cl of cells){let col=cl.light?'#D6DBC9':'#C6E84A',x=cl.x,y=cl.y,a=1,sz=cellPx-1.5;let L=cl.reg?st[cl.reg.id]:'normal';if(L==='advisory')L='normal';
      if(L==='hold'){col=cl.light?'#8E96A4':'#5C6675';}
      else if(L!=='normal'){col=L==='warning'?'#FF5C73':'#F5C542';if(cl.seed<(L==='warning'?.55:.38)&&cl.dist>.35){const amp=(L==='warning'?26:14)*cl.dist*(0.6+0.4*Math.sin(t*1.6+cl.seed*9));const ang=Math.atan2(cl.y-(g.oy+cl.reg.cy*460*g.s),cl.x-(g.ox+cl.reg.cx*220*g.s));x+=Math.cos(ang)*amp+Math.sin(t*2.1+cl.seed*7)*2;y+=Math.sin(ang)*amp+Math.cos(t*1.7+cl.seed*5)*2;a=.55+.45*Math.abs(Math.sin(t*1.3+cl.seed*11));sz=cellPx-2.5;}if(cl.light)col='#FFE9C2';}
      if(hoverR&&cl.reg===hoverR){col=cl.light?'#fff':(L==='warning'?'#FF8A9B':L==='caution'?'#FFE08A':L==='hold'?'#B5BCC8':'#E2FF6A');a=1;}
      if(opts.sel&&opts.sel()&&cl.reg&&cl.reg.id===opts.sel()){a=1;sz=cellPx-0.5;}
      bx.globalAlpha=a;bx.fillStyle=col;bx.fillRect(x-sz/2,y-sz/2,sz,sz);}
    bx.globalAlpha=1;if(!reduce||!built)requestAnimationFrame(draw);else setTimeout(()=>requestAnimationFrame(draw),400);}
  function regionAt(ev){const g=geo();const nx=(ev.clientX-g.r.left-g.ox)/(220*g.s),ny=(ev.clientY-g.r.top-g.oy)/(460*g.s);let best=null,bd=1e9;for(const r of REGIONS){const dd=Math.hypot((nx-r.cx)*0.48,ny-r.cy);if(dd<r.r*1.3&&dd<bd){bd=dd;best=r;}}return best;}
  canvas.addEventListener('mousemove',ev=>{hoverR=regionAt(ev);canvas.style.cursor=hoverR?'pointer':'default';});canvas.addEventListener('mouseleave',()=>hoverR=null);
  canvas.addEventListener('click',ev=>{const r=regionAt(ev);if(opts.onClick)opts.onClick(r,ev,geo());});
  requestAnimationFrame(draw);
  return {geo,regionPoint(r){const g=geo();return {x:g.ox+r.cx*220*g.s,y:g.oy+r.cy*460*g.s};},setHover(r){hoverR=r;}};
}

/* ---------- 추세 차트 (SVG) ---------- */
function chart(k,c,n,events){c=c||me();const data=series(k,c,n);const W=800,H=260,px=44,py=18,pr=70;const base=c.base[k],sd=c.sd[k],t=thr();
  const mn=Math.min(...data,base-sd*t[1]),mx=Math.max(...data,base+sd*t[1]);const pad=(mx-mn)*.08;const lo=mn-pad,hi=mx+pad;
  const X=i=>px+(i/(n-1))*(W-px-pr),Y=v=>py+(1-(v-lo)/(hi-lo))*(H-py-26);
  const band=(a,b,fill)=>`<rect x="${px}" y="${Y(b)}" width="${W-px-pr}" height="${Math.max(0,Y(a)-Y(b))}" fill="${fill}"/>`;
  const pts=data.map((v,i)=>`${X(i)},${Y(v)}`).join(' ');
  const ticks=[0,.25,.5,.75,1].map(f=>{const v=lo+(hi-lo)*f;return `<line x1="${px}" x2="${W-pr}" y1="${Y(v)}" y2="${Y(v)}" stroke="#161E29"/><text x="${px-8}" y="${Y(v)+3.5}" text-anchor="end">${fmt(v,k)}</text>`;}).join('');
  const xl=[0,Math.floor(n/2),n-1].map((i,j)=>`<text x="${X(i)}" y="${H-8}" text-anchor="${j===0?'start':j===2?'end':'middle'}">Sol ${SOL-(n-1-i)}</text>`).join('');
  const ev=(events||[]).filter(e=>e.crew===c.id&&SOL-e.sol<n).map(e=>{const i=n-1-(SOL-e.sol);return `<line x1="${X(i)}" x2="${X(i)}" y1="${py}" y2="${H-26}" stroke="${e.level==='warning'?'#FF5C73':e.level==='caution'?'#F5C542':'#3A4A5E'}" stroke-dasharray="3 3"/><text x="${X(i)+4}" y="${py+9}" fill="${e.level==='caution'?'#F5C542':'#7D8896'}">${e.id}</text>`;}).join('');
  const last=data[n-1];
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="${META[k].l} ${n}일 추세">
    ${band(base-sd*t[1],base+sd*t[1],'#0E1419')}${band(base-sd*t[0],base+sd*t[0],'#111A22')}${ticks}
    <line x1="${px}" x2="${W-pr}" y1="${Y(base)}" y2="${Y(base)}" stroke="#3A4A5E" stroke-dasharray="4 4"/>
    <text x="${W-pr+6}" y="${Y(base)+3.5}">기준 ${fmt(base,k)}</text>
    <text x="${W-pr+6}" y="${Y(base+sd*t[0])+3.5}" fill="#F5C542">+${t[0]}σ</text>
    <text x="${W-pr+6}" y="${Y(base-sd*t[0])+3.5}" fill="#F5C542">-${t[0]}σ</text><text x="${W-pr+6}" y="${Y(base+sd*t[1])+3.5}" fill="#FF5C73">+${t[1]}σ</text><text x="${W-pr+6}" y="${Y(base-sd*t[1])+3.5}" fill="#FF5C73">-${t[1]}σ</text>
    ${ev}<polyline fill="none" stroke="#E6EAF0" stroke-width="1.6" points="${pts}" vector-effect="non-scaling-stroke"/>
    <circle cx="${X(n-1)}" cy="${Y(last)}" r="3.5" fill="${lvl(k,c)==='caution'?'#F5C542':lvl(k,c)==='warning'?'#FF5C73':'#E6EAF0'}"/>${xl}</svg>`;}

/* ---------- 증상 분류 (키워드 · 모델 흉내) · 범주는 코드가 매핑 ---------- */
const SYM=[
  {codes:['chest_pain'],kw:['가슴','흉통','심장이 아','숨이 안','호흡곤란','숨쉬기'],warning:true,t:'가슴 통증 · 호흡곤란'},
  {codes:['dizziness'],kw:['어지','빙글','현기'],q:'일어설 때 더 심해지나요?',yes:'orthostatic',yesTxt:'일어설 때 심해짐',t:'어지러움',cat:'심혈관 적응 · 체액 이동',conds:['dehydration']},
  {codes:['nausea'],kw:['메스','구역','토할'],q:'식사 후에 시작됐나요?',t:'메스꺼움',cat:'감각운동 · 전정',conds:['sms']},
  {codes:['headache'],kw:['머리','두통','띵'],q:'빛이나 소리에 더 예민한가요?',t:'두통',cat:'환경(CO2) · 체액 이동',conds:['co2_headache']},
  {codes:['fatigue'],kw:['피곤','무기력','힘이 없'],q:'어젯밤 수면과 관련 있다고 느끼나요?',t:'피로',cat:'수면 · 피로',conds:['sleep_loss']},
  {codes:['sleep_issue'],kw:['잠','불면','못 잤'],q:'잠들기가 어려웠나요, 자주 깼나요?',t:'수면 문제',cat:'수면 · 피로',conds:['sleep_loss']}
];
function classify(text){const hits=SYM.filter(s=>s.kw.some(w=>text.includes(w)));return hits;}

/* ---------- 위험 안내 3줄 + 검증 "목록 밖 이름 없음 + 단정 표현 없음" ---------- */
function verifyScope(r){const t=(r.why||'')+' '+(r.todo||'');return (r.cond||[]).every(id=>CONDS[id])&&!/입니다|이다[.\s]|확실|진단/.test(t);}
function riskHTML(r,mode){const names=(r.cond||[]).map(id=>CONDS[id]?CONDS[id].n:id).join(' · ');
  return `<div class="risk">
    <div><span class="rk">위험 범주</span><span>${esc(r.cat)}<span class="muted"> · HRP 분류 · 규칙</span></span></div>
    <div><span class="rk">가능한 상태</span><span>${mode==='held'?'<span class="muted">보류 · 모델 출력을 버려 이름을 고르지 않았어요</span>':mode==='normal'?'<span class="muted">만들지 않음 · 판정이 정상이면 설명하지 않아요</span>':`<b>${esc(names)}</b> 가능성 · ${citeLinks(r.why)}`}</span></div>
    <div><span class="rk">오늘 할 일</span><span>${citeLinks(r.todo)}</span></div></div>`;}

window.CH={KEY,SOL,META,MK,CREW,DOCS,CHECKS,REGIONS,SYM,CONDS,ROUTINE,get S(){return S;},save,reset,load:()=>{S=load();return S;},thr,crew,me,z,rawLvl,lvl,tier,tierInfo,crewLevel:tier,fmt,sig,series,levelName,levelEn,openEvents,warnEvent,newId,autoWarn,daily,streak,exToday,routine,jo,now,clock,hhmm,shell,toast,addLog,q,esc,citeLinks,citeA,spark,tile,mountBody,rLvl,chart,classify,verifyScope,riskHTML};
})();
