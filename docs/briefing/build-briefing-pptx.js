const pptxgen = require("pptxgenjs");
const { applyTheme } = require("/Users/tylerrr/.claude/skills/synced/fa5a4705-574d-41af-b564-6e567a558aa2_49aaf5af-1144-4cd2-9d96-94bd75b23e2b/pptx/scripts/apply_theme.js");

const THEME = {
  name: "SpaceApps Briefing",
  headFontFace: "Malgun Gothic",
  bodyFontFace: "Malgun Gothic",
  colors: {
    dk1: "111C30", lt1: "F4F5F7", dk2: "1A2A47", lt2: "E6E9EF",
    accent1: "F2B705", accent2: "6FB1FF", accent3: "4E5A6E", accent4: "B9C4D6",
    accent5: "2E7D5B", accent6: "C0392B", hlink: "6FB1FF", folHlink: "4E5A6E",
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "11/14 운영진 안내 요약";
pres.author = "Tyler";
const C = pres.SchemeColor;
const W = 13.33, H = 7.5, M = 0.6;

// Layouts
pres.defineSlideMaster({
  title: "DARK", background: { color: C.text1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.7, w: W - 2 * M, h: 1.1, fontSize: 40, bold: true, color: C.background1, margin: 0, align: "left" }, text: "" } },
    { text: { text: "NASA Space Apps Seoul 2026 · 팀 공유", options: { x: M, y: H - 0.55, w: 8, h: 0.3, fontSize: 10, color: C.accent4, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: H - 0.55, w: 0.6, h: 0.3, fontSize: 10, color: C.accent4, align: "right" },
});
pres.defineSlideMaster({
  title: "LIGHT", background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.5, w: W - 2 * M, h: 0.9, fontSize: 36, bold: true, color: C.text1, margin: 0, align: "left" }, text: "" } },
    { text: { text: "NASA Space Apps Seoul 2026 · 팀 공유", options: { x: M, y: H - 0.55, w: 8, h: 0.3, fontSize: 10, color: C.accent3, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: H - 0.55, w: 0.6, h: 0.3, fontSize: 10, color: C.accent3, align: "right" },
});
pres.defineSlideMaster({
  title: "LIGHT2", background: { color: C.background2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: M, y: 0.5, w: W - 2 * M, h: 0.9, fontSize: 36, bold: true, color: C.text1, margin: 0, align: "left" }, text: "" } },
    { text: { text: "NASA Space Apps Seoul 2026 · 팀 공유", options: { x: M, y: H - 0.55, w: 8, h: 0.3, fontSize: 10, color: C.accent3, margin: 0 } } },
  ],
  slideNumber: { x: W - M - 0.6, y: H - 0.55, w: 0.6, h: 0.3, fontSize: 10, color: C.accent3, align: "right" },
});

function card(slide, x, y, w, h, { fill, title, body, titleColor, bodyColor, big }) {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill }, line: { color: fill }, rectRadius: 0.12, objectName: "card" });
  if (big) {
    slide.addText(big, { x: x + 0.25, y: y + 0.2, w: w - 0.5, h: 0.75, fontSize: 32, bold: true, color: C.accent1, margin: 0, isTextBox: true });
    slide.addText(title, { x: x + 0.25, y: y + 0.95, w: w - 0.5, h: 0.4, fontSize: 14, color: titleColor, margin: 0, isTextBox: true });
    if (body) slide.addText(body, { x: x + 0.25, y: y + 1.35, w: w - 0.5, h: h - 1.5, fontSize: 13, color: bodyColor, margin: 0, isTextBox: true, valign: "top" });
  } else {
    slide.addText(title, { x: x + 0.25, y: y + 0.2, w: w - 0.5, h: 0.45, fontSize: 18, bold: true, color: titleColor, margin: 0, isTextBox: true });
    slide.addText(body, { x: x + 0.25, y: y + 0.7, w: w - 0.5, h: h - 0.9, fontSize: 13, color: bodyColor, margin: 0, isTextBox: true, valign: "top" });
  }
}
const bullets = (items) => items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 6 } }));
const tblHead = (cells, widths) => cells.map((c, i) => ({ text: c, options: { bold: true, color: "F4F5F7", fill: { color: "1A2A47" } } }));

// 1 Cover
pres.addSection({ title: "핵심" });
let s = pres.addSlide({ masterName: "DARK", sectionTitle: "핵심" });
s.addText("11/14 운영진 안내 요약", { placeholder: "title" });
s.addText("08:00 Zoom 안내(29분)에서 나온 제출 규정, 심사, 체크인, 팀 미팅 정리. 녹화·녹음 기준이라 세부는 NASA 최신 가이드가 우선.", { x: M, y: 1.9, w: 11, h: 0.9, fontSize: 16, color: C.accent4, margin: 0, isTextBox: true });
const cw = (W - 2 * M - 0.6) / 3;
[["11/15 23:59", "제출 마감 (권장 23:55)"], ["7장 / 30초", "슬라이드 또는 영상, 둘 중 하나"], ["3 + 1", "개인 체크인 3회 + 팀 미팅 1회"]].forEach(([n, l], i) => {
  card(s, M + i * (cw + 0.3), 3.3, cw, 2.2, { fill: "1A2A47", big: n, title: l, titleColor: "B9C4D6" });
});
s.addNotes("심사는 프로젝트 페이지로만, 발표 없음.");

// 2 Glance
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "핵심" });
s.addText("한눈에 보는 핵심", { placeholder: "title" });
const glance = [
  ["발표 없음", "심사는 공식 프로젝트 페이지와 거기 걸린 공개 링크로만. 채팅 Q&A에서 운영진이 확인."],
  ["전부 영어", "이름, 요약, 슬라이드, 상세 모두 영어. 다른 언어 영상은 영어 자막. 글로벌 심사로 넘어가기 때문."],
  ["전부 공개", "로그인 없이 누구나 열리는 링크만. NASA 본부도 검토. 로고와 미성년자 정보 금지."],
  ["AI 사용 가능", "어떤 도구를 어디에 어떻게 썼는지 프로젝트 페이지에 기록. 제출 폼 선택 항목도 체크."],
  ["NASA 리소스 1개 이상", "글로벌 어워드 자격 조건. 우리 챌린지 Resources는 HRP 페이지 3개와 CSA 기사 2개뿐."],
  ["제출 버튼 확인", "Save Progress는 제출이 아니다. Submit for Judging을 누르고 성공 메시지까지 확인."],
];
glance.forEach(([t, b], i) => {
  const col = i % 3, row = Math.floor(i / 3);
  card(s, M + col * (cw + 0.3), 1.6 + row * 2.6, cw, 2.35, { fill: "E6E9EF", title: t, body: b, titleColor: "111C30", bodyColor: "4E5A6E" });
});

// 3 Submit
pres.addSection({ title: "제출물과 규정" });
s = pres.addSlide({ masterName: "LIGHT2", sectionTitle: "제출물과 규정" });
s.addText("제출물", { placeholder: "title" });
const rows3 = [
  tblHead(["항목", "형식", "주의"]),
  ["프로젝트 이름", "영어", "한눈에 들어오게. 운영진이 매우 중요하다고 강조"],
  ["High-Level Summary", "영어 50–200단어", "무엇을 만들었나, 어떤 문제와 해결책, 왜 중요한가"],
  ["Project Demo", "슬라이드 최대 7장(제목 포함) 또는 30초 이하 영상", "외부에 올린 공개 링크 1개. 영어, 타 언어 영상은 영어 자막"],
  ["Project Details", "서술 + 이미지(JPG·PNG·GIF 10MB), 영상은 링크", "하는 일, 작동·설계 방식, 이점·목표, 도구·언어·HW·SW"],
  ["References", "출처·링크·라이선스", "인용이 사용 허락을 대신하지 않는다"],
];
s.addTable(rows3, { x: M, y: 1.55, w: W - 2 * M, colW: [2.6, 4.2, 5.33], fontSize: 12, color: "111C30", fill: { color: "F4F5F7" }, border: { type: "solid", color: "D0D5DE", pt: 0.75 }, rowH: 0.55, valign: "middle", margin: 0.08 });
s.addShape(pres.ShapeType.roundRect, { x: M, y: 5.35, w: W - 2 * M, h: 1.25, fill: { color: "F2B705" }, line: { color: "F2B705" }, rectRadius: 0.1, objectName: "callout" });
s.addText("예시 7장(필수 아님): 제목·팀·챌린지·문제 → 문제와 대상 → 해결책·핵심 기능 → 화면·UX → NASA 데이터 활용 → 구현·설계 이유·결과 → 기대 효과·다음 단계·출처. 슬라이드는 PPT·Google Slides를 외부에 올리고 공개 링크로 제출.", { x: M + 0.25, y: 5.45, w: W - 2 * M - 0.5, h: 1.05, fontSize: 13, color: "111C30", margin: 0, isTextBox: true, valign: "middle" });

// 4 Rules
s = pres.addSlide({ masterName: "DARK", sectionTitle: "제출물과 규정" });
s.addText("공개·금지 사항", { placeholder: "title" });
s.addText("하나라도 어기면 좋은 프로젝트여도 공개와 글로벌 추천이 불가능하다.", { x: M, y: 1.75, w: 11.5, h: 0.4, fontSize: 15, color: C.accent4, margin: 0, isTextBox: true });
const half = (W - 2 * M - 0.5) / 2;
s.addText("하지 말 것", { x: M, y: 2.4, w: half, h: 0.45, fontSize: 20, bold: true, color: C.accent1, margin: 0, isTextBox: true });
s.addText(bullets(["NASA 로고를 팀·프로젝트 브랜드로 쓰거나 승인을 암시", "AI 생성 이미지에 NASA 로고·깃발·미션 식별자", "18세 미만의 식별 가능한 이름·목소리·모습", "비공개 코드·기밀·개인정보, 개인 소장 자료"]), { x: M, y: 2.95, w: half, h: 3.3, fontSize: 15, color: C.background1, margin: 0, isTextBox: true, valign: "top" });
s.addText("해야 할 것", { x: M + half + 0.5, y: 2.4, w: half, h: 0.45, fontSize: 20, bold: true, color: C.accent1, margin: 0, isTextBox: true });
s.addText(bullets(["원본은 자유 이용 또는 OSI 라이선스. 미지정 시 NASA가 Apache 2.0으로 배포", "공개 NASA 사진은 출처와 이용 조건 확인 후 출처 표기", "AI 도구 사용 내역을 프로젝트 페이지에 공개", "미국 외 기관 데이터는 해당 사이트 이용 조건 준수"]), { x: M + half + 0.5, y: 2.95, w: half, h: 3.3, fontSize: 15, color: C.background1, margin: 0, isTextBox: true, valign: "top" });

// 5 Judging
pres.addSection({ title: "심사와 시상" });
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "심사와 시상" });
s.addText("심사 기준과 심사위원", { placeholder: "title" });
const rows5 = [
  tblHead(["기준", "보는 것"]),
  ["Impact 임팩트", "문제의 중요성과 기대 효과"],
  ["Creativity 창의성", "새로운 접근과 독창성"],
  ["Validity 타당성", "과학적 근거와 방법의 타당성"],
  ["Relevance 관련성", "선택한 챌린지와 해결책의 연결"],
  ["Presentation 전달력", "설명과 시각 자료의 명확성"],
];
s.addTable(rows5, { x: M, y: 1.6, w: half, colW: [2.4, half - 2.4], fontSize: 13, color: "111C30", fill: { color: "E6E9EF" }, border: { type: "solid", color: "D0D5DE", pt: 0.75 }, rowH: 0.5, valign: "middle", margin: 0.08 });
s.addText("심사위원이 독립 평가하고 개별 점수는 공개하지 않는다.", { x: M, y: 4.8, w: half, h: 0.4, fontSize: 12, color: C.accent3, margin: 0, isTextBox: true });
s.addText("심사위원 4명", { x: M + half + 0.5, y: 1.6, w: half, h: 0.45, fontSize: 20, bold: true, color: C.text1, margin: 0, isTextBox: true });
s.addText(bullets(["박성홍 박사, 한국천문연구원(KASI). NASA 글로벌 심사 추천위원으로도 활동", "박현우 교수, 서울대 데이터사이언스대학원", "유원두 리드, AWS Aerospace & Satellite Solutions 한국 비즈니스 리드", "이수경 교수, 연세대 컴퓨터과학과"]), { x: M + half + 0.5, y: 2.15, w: half, h: 2.6, fontSize: 14, color: "111C30", margin: 0, isTextBox: true, valign: "top" });
s.addShape(pres.ShapeType.roundRect, { x: M + half + 0.5, y: 4.95, w: half, h: 1.1, fill: { color: "F2B705" }, line: { color: "F2B705" }, rectRadius: 0.1, objectName: "callout" });
s.addText("교수·전문가라 학문적 기준이 높다. 설계와 선택의 이유를 디테일로 설득할 것.", { x: M + half + 0.75, y: 5.05, w: half - 0.5, h: 0.9, fontSize: 13, color: "111C30", margin: 0, isTextBox: true, valign: "middle" });

// 6 Awards
s = pres.addSlide({ masterName: "DARK", sectionTitle: "심사와 시상" });
s.addText("서울 시상과 인증서", { placeholder: "title" });
[["Top 3", "종합 심사점수 1~3위", "글로벌 추천 대상"], ["1~7팀", "Honorable Mentions", "4~10위 중 글로벌 추천 가능 수에 따라 선정"], ["10부문", "Recognition 특별상", "프로젝트별 강점을 부문별로 인정"]].forEach(([n, l, b], i) => {
  card(s, M + i * (cw + 0.3), 1.8, cw, 2.3, { fill: "1A2A47", big: n, title: l, body: b, titleColor: "B9C4D6", bodyColor: "F4F5F7" });
});
s.addText("동점 기준", { x: M, y: 4.5, w: half, h: 0.4, fontSize: 18, bold: true, color: C.accent1, margin: 0, isTextBox: true });
s.addText("팀 참가가 단독보다 우선. 팀 간에는 인원이 많은 팀 우선. 참가·완주 요건과 규정을 충족한 프로젝트만 대상.", { x: M, y: 4.95, w: half, h: 1.3, fontSize: 14, color: C.background1, margin: 0, isTextBox: true, valign: "top" });
s.addText("인증서 조건 두 가지", { x: M + half + 0.5, y: 4.5, w: half, h: 0.4, fontSize: 18, bold: true, color: C.accent1, margin: 0, isTextBox: true });
s.addText("1. Submit for Judging 완료 (11/15 23:59 KST)\n2. 서울 출석: 개인 체크인 + 필수 팀 미팅. 인증서 이름은 등록한 이름 그대로이니 미리 확인.", { x: M + half + 0.5, y: 4.95, w: half, h: 1.3, fontSize: 14, color: C.background1, margin: 0, isTextBox: true, valign: "top" });

// 7 Meeting
pres.addSection({ title: "체크인·일정·할 일" });
s = pres.addSlide({ masterName: "LIGHT2", sectionTitle: "체크인·일정·할 일" });
s.addText("체크인과 팀 미팅", { placeholder: "title" });
s.addText("체크인 5회 중 4회 필수, 그중 1회는 팀 미팅으로 대체. 개인 체크인 3회 + 팀 미팅 1회. 체크인은 Zoom 공지 시간에만, 본인이 직접.", { x: M, y: 1.5, w: W - 2 * M, h: 0.5, fontSize: 14, color: C.accent3, margin: 0, isTextBox: true });
const rows7 = [
  tblHead(["미팅룸 A (KST)", "단계", "운영진"]),
  ["11/14 10:00–13:00", "시작", "선민·경환 (영어 가능)"],
  ["11/14 15:00–17:00", "시작 또는 설계", "확인 필요"],
  ["11/14 20:00–22:00", "아이디어·설계", "선민·성은·현지"],
  ["11/15 11:00–14:00", "제작", "선민·우빈 (영어 가능)"],
];
s.addTable(rows7, { x: M, y: 2.2, w: half, colW: [2.4, 1.8, half - 4.2], fontSize: 12, color: "111C30", fill: { color: "F4F5F7" }, border: { type: "solid", color: "D0D5DE", pt: 0.75 }, rowH: 0.48, valign: "middle", margin: 0.08 });
s.addText("팀당 1회 15분, 전원 참석 카메라 ON. 대표 한 명이 예약. 08:00 참석자 우선, 09:00부터 선착순. 예약 입력: 등록 팀명, 팀 페이지 URL, 대표 이름·이메일, 전원 등록 이메일.", { x: M, y: 4.8, w: half, h: 1.3, fontSize: 12, color: C.accent3, margin: 0, isTextBox: true, valign: "top" });
[["시작", "팀 대표가 챌린지 설명. 각자 맡은 역할과 첫 작업."], ["아이디어·설계", "누구를 위한 프로젝트인지, 어떤 데이터로 무엇을 만들 계획인지. 각자 맡은 부분과 구현 방법."], ["제작", "지금까지 결과물 시연. 각자 한 것과 할 것."]].forEach(([t, b], i) => {
  card(s, M + half + 0.5, 2.2 + i * 1.35, half, 1.2, { fill: "F4F5F7", title: t, body: b, titleColor: "111C30", bodyColor: "4E5A6E" });
});

// 8 Schedule
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "체크인·일정·할 일" });
s.addText("일정과 링크", { placeholder: "title" });
const rows8 = [
  tblHead(["항목", "시간 (KST)", "비고"]),
  ["해커톤 시작", "11/14 09:00", "프로젝트 탭도 이때 열림"],
  ["DAY 1 Zoom", "11/14 08:00 – 11/15 00:15", "회의 ID 886 9387 0703"],
  ["DAY 2 Zoom", "11/15 00:15 – 11/16 01:00", "회의 ID 828 4689 1548. 야간 작업 팀은 이 링크로 재접속"],
  ["포토타임", "매일 14:30", "선착순 10팀. 인스타그램에 팀 사진 올리고 태그"],
  ["제출 권장", "11/15 23:55", "공식 마감 23:59. 사이트가 느리니 미리"],
  ["글로벌 추천 발표", "11/19", "운영진 언급, 확인 필요"],
];
s.addTable(rows8, { x: M, y: 1.55, w: W - 2 * M, colW: [2.6, 3.6, 5.93], fontSize: 13, color: "111C30", fill: { color: "E6E9EF" }, border: { type: "solid", color: "D0D5DE", pt: 0.75 }, rowH: 0.52, valign: "middle", margin: 0.08 });
s.addText("Zoom 표시 이름은 [팀명] 또는 [팀명-이름]. 메인 회의실에서는 마이크 끄기. 운영진 미팅에서는 카메라 필수. 링크는 D-1 메일(11/13)과 팀 공유 문서에 있다.", { x: M, y: 5.5, w: W - 2 * M, h: 0.8, fontSize: 13, color: C.accent3, margin: 0, isTextBox: true });

// 9 Todo
s = pres.addSlide({ masterName: "DARK", sectionTitle: "체크인·일정·할 일" });
s.addText("우리 팀 할 일", { placeholder: "title" });
s.addText("지금", { x: M, y: 1.75, w: half, h: 0.4, fontSize: 20, bold: true, color: C.accent1, margin: 0, isTextBox: true });
s.addText(bullets(["팀 미팅 예약: 대표 1명, 전원 가능한 시간. 설계(11/14 20–22시) 또는 제작(11/15 11–14시) 단계", "등록 팀명, 팀 페이지 URL, 전원 등록 이메일 모아두기", "프로젝트 페이지에 팀원 4명 전원 등록 확인", "슬라이드 7장 또는 30초 영상 중 택1, 담당 정하기"]), { x: M, y: 2.25, w: half, h: 3.0, fontSize: 14, color: C.background1, margin: 0, isTextBox: true, valign: "top" });
s.addText("제출 전", { x: M + half + 0.5, y: 1.75, w: half, h: 0.4, fontSize: 20, bold: true, color: C.accent1, margin: 0, isTextBox: true });
s.addText(bullets(["AI 사용 내역 기록: SLM 역할, 파인튜닝, 코딩 도구", "NASA 리소스 1개 이상 사용 명시 (HRP Hazards·Risks·Research)", "임계값·규칙의 근거 출처를 References에 라이선스와 함께", "NASA 로고 금지, AI 이미지에 NASA 브랜드 금지", "모든 링크 로그아웃 상태에서 테스트, 레포 공개 + OSI 라이선스", "11/15 23:55까지 Submit for Judging, 성공 메시지 확인"]), { x: M + half + 0.5, y: 2.25, w: half, h: 3.2, fontSize: 14, color: C.background1, margin: 0, isTextBox: true, valign: "top" });
s.addShape(pres.ShapeType.roundRect, { x: M, y: 5.55, w: W - 2 * M, h: 1.0, fill: { color: "F2B705" }, line: { color: "F2B705" }, rectRadius: 0.1, objectName: "callout" });
s.addText("미확인: 행사 전에 만든 학습셋·어댑터·스크립트 사용 가능 여부. 08:00 안내에 질문도 답도 없었다. 팀 미팅이나 Space Apps Connect에서 묻는다. 안 된다면 행사 중 재학습으로 대체(8B 기준 약 45분).", { x: M + 0.25, y: 5.6, w: W - 2 * M - 0.5, h: 0.9, fontSize: 13, color: "111C30", margin: 0, isTextBox: true, valign: "middle" });

(async () => {
  const out = process.argv[2];
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out);
})();
