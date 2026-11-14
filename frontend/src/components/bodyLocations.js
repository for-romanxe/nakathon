// bodyLocations.js — where a symptom report says it hurts (step 1 of the body-location plan, team 11/14).
// When the backend sends event.locations (step 2), that is used as is. Until then the frontend looks for body
// words in the report text itself. Display only: it places a mark on the body and never changes a verdict.
import { REGION_BY_LOCATION } from './bodyRegions.js'

// Limbs need a side: "<side> <part>" (en) / "<side>(쪽|측) <part>" (ko). "both"/"양쪽" marks both sides.
const ARM_EN = 'arms?|hands?|wrists?|shoulders?|elbows?|forearms?'
const LEG_EN = 'legs?|knees?|ankles?|feet|foot|thighs?|calf|calves|shins?|hips?'
const ARM_KO = '팔꿈치|팔목|손목|어깨|팔|손'
const LEG_KO = '허벅지|종아리|정강이|무릎|발목|다리|발|고관절'

// JS \b only knows ASCII letters, so Korean words get their own edges: not right after another Hangul syllable,
// and followed by a particle, punctuation, space or the end — "팔이", "다리가", "무릎:" match; "팔찌", "다리미",
// "팔십", "머리카락" do not.
const KO_START = '(?<![가-힣])'
const KO_END = '(?=[이가은는을를도에의와과랑만:\\s.,!?~)]|$)'
const SIDED = [
  new RegExp(`\\b(left|right|both)\\s+(?:(${ARM_EN})|(${LEG_EN}))\\b`, 'gi'),
  new RegExp(`(왼|오른|양)\\s*(?:쪽|측)?\\s*(?:(${ARM_KO})|(${LEG_KO}))${KO_END}`, 'g'),
]
// a limb named without a side; single-syllable 발/손 are left out here (발열 = fever, 손님 …)
const UNSIDED = [
  { limb: 'arm', re: new RegExp(`\\b(?:${ARM_EN})\\b|${KO_START}(?:팔꿈치|팔목|손목|어깨|팔)${KO_END}`, 'i') },
  { limb: 'leg', re: new RegExp(`\\b(?:${LEG_EN})\\b|${KO_START}(?:허벅지|종아리|정강이|무릎|발목|다리|고관절)${KO_END}`, 'i') },
]
const TRUNK = [
  { location: 'head', re: new RegExp(`\\bhead(?:ache)?\\b|\\bmigraine\\b|${KO_START}머리${KO_END}|두통`, 'i') },
  { location: 'chest', re: /\bchest\b|가슴|흉통/i },
  { location: 'abdomen', re: /\bstomach\b|\babdom\w*|\bbelly\b|복통|복부|배(?=[\s:가는이를도])/i },
]

function sideOf(word) {
  if (/^(left|왼)/i.test(word)) return ['left']
  if (/^(right|오른)/i.test(word)) return ['right']
  return ['left', 'right'] // both / 양
}

// A report can deny one part while naming another ("가슴 통증은 없고 오른쪽 팔만 아파요", "no chest pain but my right
// arm hurts"). The text is cut into clauses, and a clause that denies pain or a problem names no part. Only pain
// / trouble denials count: "왼팔에 힘이 없어요" or "no strength in my left arm" are symptoms, not denials.
const CLAUSE = /[,.;!?\n]|\s(?:but|and|although|though|while)\s|(?:고|는데|은데|지만|면서)(?=\s)|그리고|하지만|그런데/i
const DENIAL = new RegExp([
  '\\bno\\s+(?:\\w+\\s+)?(?:pain|ache|headaches?|migraines?|problems?|issues?|soreness|discomfort)\\b',
  "\\b(?:doesn'?t|does not|don'?t|do not|isn'?t|is not|aren'?t|are not)\\s+(?:hurt|ache|have|feel|sore|painful)",
  '\\bwithout\\s+(?:\\w+\\s+)?pain\\b',
  "(?:\\bis|'s|\\bare|'re|\\bfeels?)\\s+(?:fine|okay|ok|normal|better)\\b",
  '\\b(?:no longer|not anymore)\\b',
  '(?:통증|아픔|증상|문제|이상|두통|흉통|복통)(?:은|는|이|가|도)?\\s*없',
  '(?:아프|저리|쑤시)지\\s*(?:는\\s*)?않',
  '안\\s*(?:아프|아파|저리|저려|쑤시|쑤셔)',
  '괜찮',
].join('|'), 'i')

// "It hurt, but it's fine now": a denial clause that names no part of its own takes back the clause before it,
// when that clause is in the past ("아팠는데", "hurt earlier") or the denial says "now" ("지금은 괜찮아요",
// "fine now", "anymore"). Without either ("왼쪽 다리가 아파요. 다른 데는 괜찮아요") the earlier part stays.
const PAST = /(?:았|었|였|했)|\b(?:was|were|had|hurt earlier|ached|earlier|yesterday|before|used to)\b/i
const NOW = /지금|이제|현재|더\s*이상|\b(?:now|anymore|any more|no longer)\b/i

// parts named in one clause, before any denial is applied: [{ location, sideStated }]
function partsIn(clause) {
  const found = []
  const sidedLimb = { arm: false, leg: false }
  for (const re of SIDED) {
    for (const m of clause.matchAll(re)) {
      const limb = m[2] ? 'arm' : 'leg'
      sidedLimb[limb] = true
      for (const side of sideOf(m[1])) found.push({ location: `${side}_${limb}`, sideStated: true })
    }
  }
  for (const { limb, re } of UNSIDED) {
    if (!sidedLimb[limb] && re.test(clause)) {
      found.push({ location: `left_${limb}`, sideStated: false }, { location: `right_${limb}`, sideStated: false })
    }
  }
  for (const { location, re } of TRUNK) if (re.test(clause)) found.push({ location, sideStated: true })
  return found
}

// text -> [{ location, sideStated }] (parts named in clauses that are not denied or taken back)
export function locationsInText(text) {
  if (!text) return []
  // curly or typographic apostrophes (’ ‘ ` ´) read as a plain one, so "doesn’t" is "doesn't"
  const clauses = text.replace(/[’‘`´]/g, "'").split(CLAUSE).filter(Boolean)
  const kept = clauses.map((clause) => (DENIAL.test(clause) ? [] : partsIn(clause)))
  clauses.forEach((clause, i) => {
    if (i === 0 || !DENIAL.test(clause) || partsIn(clause).length > 0) return
    if (PAST.test(clauses[i - 1]) || NOW.test(clause)) kept[i - 1] = []
  })
  const out = new Map()
  for (const { location, sideStated } of kept.flat()) {
    const prev = out.get(location)
    if (!prev || (sideStated && !prev.sideStated)) out.set(location, { location, sideStated })
  }
  return [...out.values()]
}

// Today's reports per region: { [regionId]: [{ event, source: 'backend' | 'text', sideStated }] }
export function reportsByRegion(events) {
  const byRegion = {}
  for (const e of events ?? []) {
    if (!e.symptom_text && !Array.isArray(e.locations)) continue
    const found = Array.isArray(e.locations)
      ? e.locations.map((location) => ({ location, sideStated: true, source: 'backend' }))
      : locationsInText(e.symptom_text).map((l) => ({ ...l, source: 'text' }))
    for (const { location, sideStated, source } of found) {
      const region = REGION_BY_LOCATION[location]
      if (!region) continue
      ;(byRegion[region] ??= []).push({ event: e, source, sideStated })
    }
  }
  return byRegion
}
