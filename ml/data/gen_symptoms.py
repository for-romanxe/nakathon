"""증상 문장 → enum JSON 학습셋 생성기 (ko/en, 템플릿 조합).

출력: train.jsonl / valid.jsonl (mlx-lm chat 형식), schema.json
라벨은 문장에 들어간 표현으로만 정한다(v2, 2026-11-14): 세기를 말하지 않으면 기본값, needs_question 은 규칙으로만.
평가용 문항은 따로 쓴다.
"""
import json, random, re, pathlib, argparse

random.seed(20261112)
HERE = pathlib.Path(__file__).parent

CODES = ["chest_pain", "shortness_of_breath", "dizziness", "nausea", "headache",
         "fatigue", "sleep_issue", "musculoskeletal_pain", "congestion", "skin_rash",
         "vision_change", "low_mood", "crisis", "none"]
ONSET = ["now", "hours", "today", "days", "unknown"]
WORSE = ["standing", "after_meal", "exercise", "lying", "none", "unknown"]

SYSTEM = (
    "You extract symptom codes from a crew member's free-text report. "
    "Answer with JSON only. codes: array from " + json.dumps(CODES) +
    ". onset: one of " + json.dumps(ONSET) + ". worse_when: one of " + json.dumps(WORSE) +
    ". severity: integer 1-5. needs_question: true when a single follow-up question would change the codes. "
    "Never invent codes outside the list."
)

# 코드별 표현 (ko, en). 한 코드에 여러 말투.
PH = {
    "chest_pain": (["가슴이 아파요", "가슴이 답답하고 쥐어짜는 느낌이에요", "흉통이 있어요", "가슴 가운데가 눌리는 것 같아요", "심장 쪽이 찌릿해요", "가슴이 조여요"],
                   ["my chest hurts", "I have a tight, squeezing feeling in my chest", "chest pain", "pressure in the middle of my chest", "sharp pain near my heart"]),
    "shortness_of_breath": (["숨이 잘 안 쉬어져요", "숨이 차요", "호흡이 가빠요", "숨쉬기가 힘들어요", "가만히 있어도 숨이 가빠요"],
                            ["I can't catch my breath", "I'm short of breath", "breathing is hard", "I feel winded even at rest"]),
    "dizziness": (["어지러워요", "머리가 빙글빙글 돌아요", "현기증이 나요", "핑 돌아요", "어질어질해요", "세상이 빙 돌아요"],
                  ["I feel dizzy", "the room is spinning", "I'm lightheaded", "I get woozy", "vertigo"]),
    "nausea": (["메스꺼워요", "속이 울렁거려요", "토할 것 같아요", "구역질이 나요", "속이 안 좋아요"],
               ["I feel nauseous", "my stomach is churning", "I feel like throwing up", "queasy"]),
    "headache": (["머리가 아파요", "두통이 있어요", "머리가 띵해요", "관자놀이가 지끈거려요", "머리가 무거워요", "뒷골이 당겨요"],
                 ["I have a headache", "my head is pounding", "my head feels heavy", "throbbing at my temples", "dull headache"]),
    "fatigue": (["너무 피곤해요", "무기력해요", "힘이 하나도 없어요", "몸이 축 처져요", "기운이 없어요", "계속 졸려요"],
                ["I'm exhausted", "no energy at all", "I feel drained", "I'm sluggish", "so tired"]),
    "sleep_issue": (["잠을 거의 못 잤어요", "밤에 자꾸 깼어요", "잠이 안 와요", "불면이에요", "새벽에 깨서 다시 못 잤어요", "세 시간밖에 못 잤어요"],
                    ["I barely slept", "I kept waking up", "I can't fall asleep", "insomnia", "woke at 3 and couldn't go back to sleep"]),
    "musculoskeletal_pain": (["허리가 아파요", "목이 뻐근해요", "어깨가 결려요", "등이 쑤셔요", "무릎이 아파요", "허리가 뻣뻣해요"],
                             ["my back hurts", "stiff neck", "my shoulder aches", "lower back pain", "my knee hurts"]),
    "congestion": (["코가 막혀요", "목이 따가워요", "콧물이 나요", "목이 칼칼하고 기침이 나요", "코가 꽉 막혔어요"],
                   ["my nose is stuffed", "sore throat", "runny nose", "scratchy throat and a cough", "congested"]),
    "skin_rash": (["팔에 발진이 났어요", "피부가 가려워요", "손목에 붉은 반점이 생겼어요", "등에 두드러기가 났어요"],
                  ["I have a rash on my arm", "my skin is itchy", "red spots on my wrist", "hives on my back"]),
    "vision_change": (["눈이 침침해요", "시야가 흐릿해요", "눈이 뻑뻑하고 아파요", "글씨가 잘 안 보여요", "눈 뒤쪽이 묵직해요"],
                      ["my vision is blurry", "things look fuzzy", "my eyes feel dry and sore", "hard to read small text", "pressure behind my eyes"]),
    "low_mood": (["오늘 꿀꿀해요", "기분이 가라앉아요", "아무것도 하기 싫어요", "괜히 우울해요", "짜증이 계속 나요", "불안해요", "마음이 무거워요"],
                 ["I feel down today", "I'm in a low mood", "I don't feel like doing anything", "I feel anxious", "irritable all day"]),
    "crisis": (["죽고 싶어요", "다 끝내고 싶어요", "살고 싶지 않아요", "사라지고 싶어요"],
               ["I want to die", "I want it all to end", "I don't want to be alive", "I wish I could disappear"]),
}
NONE_PH = (["오늘은 특별한 증상 없어요", "괜찮아요", "별 일 없어요", "컨디션 좋아요", "아픈 데 없어요", "그냥 평소 같아요"],
           ["no symptoms today", "I'm fine", "nothing to report", "feeling good", "all normal"])

ONSET_PH = {
    "now": (["방금부터", "지금", "조금 전부터"], ["just now", "right now", "since a moment ago"]),
    "hours": (["몇 시간 전부터", "오후부터", "두세 시간째"], ["for a few hours", "since this afternoon", "for the last couple of hours"]),
    "today": (["오늘 아침부터", "일어났을 때부터", "오늘 하루 종일", "오전부터"], ["since I woke up", "all day today", "since this morning when I got up", "since this morning"]),
    "days": (["며칠째", "이틀 전부터", "지난주부터", "사흘 정도"], ["for a few days", "since two days ago", "since last week", "about three days now"]),
}
WORSE_PH = {
    "standing": (["일어설 때 더 심해요", "서 있으면 더 심해요", "일어나면 심해져요"], ["worse when I stand up", "it gets worse standing", "standing makes it worse"]),
    "after_meal": (["밥 먹고 나면 더해요", "식사 후에 더 심해요"], ["worse after eating", "it gets worse after meals"]),
    "exercise": (["운동하면 더 심해요", "운동 중에 더 그래요", "ARED 하고 나면 더 심해요"], ["worse during exercise", "gets worse when I work out", "worse after the treadmill"]),
    "lying": (["누우면 더 심해요", "자려고 누우면 더 그래요"], ["worse lying down", "worse when I lie down"]),
    "none": (["뭘 해도 비슷해요", "특별히 더 심해지는 건 없어요"], ["same no matter what I do", "nothing makes it worse"]),
}
SEV_PH = {
    1: (["아주 약해요", "살짝이에요", "조금이요"], ["it's mild", "just a little", "barely noticeable"]),
    2: (["약간 그래요", "좀 그래요"], ["somewhat", "a bit"]),
    3: (["꽤 거슬려요", "신경 쓰일 정도예요"], ["it's quite bothersome", "noticeable enough to bother me"]),
    4: (["많이 심해요", "일하기 힘들 정도예요"], ["it's bad", "bad enough that it's hard to work"]),
    5: (["너무 심해서 못 견디겠어요", "최악이에요", "참기 힘들어요"], ["it's unbearable", "the worst it's been", "I can't stand it"]),
}
FILL = (["", "", "", "음, ", "저기, ", "보고합니다. ", "체크인이요. ", "그리고 "], ["", "", "", "um, ", "hey, ", "reporting: ", "check-in: ", "also "])

def pick(pair, lang):
    return random.choice(pair[0] if lang == "ko" else pair[1])

def join(parts, lang):
    parts = [p for p in parts if p]
    return (" ".join(parts) if lang == "ko" else ", ".join(parts))

def make(lang):
    r = random.random()
    if r < 0.06:
        text = pick(FILL, lang) + pick(NONE_PH, lang)
        return text, {"codes": ["none"], "onset": "unknown", "worse_when": "unknown", "severity": 1, "needs_question": False}
    k = 2 if random.random() < 0.3 else 1
    codes = random.sample([c for c in CODES if c != "none"], k)
    onset = random.choices(ONSET, weights=[2, 3, 3, 3, 3])[0]
    worse = "unknown"
    if "dizziness" in codes and random.random() < 0.5:
        worse = "standing"
    elif random.random() < 0.3:
        worse = random.choice([w for w in WORSE if w != "unknown"])
    sev = random.choices([1, 2, 3, 4, 5], weights=[2, 3, 3, 2, 1])[0]
    if "crisis" in codes:
        sev = max(sev, 4)
    if "chest_pain" in codes or "shortness_of_breath" in codes:
        sev = max(sev, 3)
    sev_part = pick(SEV_PH[sev], lang) if random.random() < 0.6 else ""
    if not sev_part:      # 세기를 말하지 않은 문장: 기본 2, 흉통·호흡곤란은 3 이상, 위기는 4 이상
        sev = 4 if "crisis" in codes else 3 if ("chest_pain" in codes or "shortness_of_breath" in codes) else 2
    fill = pick(FILL, lang)
    parts = []
    for i, c in enumerate(codes):
        ph = pick(PH[c], lang)
        if i == 0 and onset != "unknown":
            if random.random() < 0.85:
                ph = pick(ONSET_PH[onset], lang) + " " + ph
            else:
                onset = "unknown"  # 문장에 없으면 라벨도 모름
        parts.append(ph)
    if sev_part:
        parts.append(sev_part)
    if worse != "unknown":
        parts.append(pick(WORSE_PH[worse], lang))
    text = re.sub(r"\s+", " ", fill + join(parts, lang)).strip()
    if random.random() < 0.2:
        text = text.rstrip(".") + ("." if lang == "en" else "")
    if random.random() < 0.1:
        text = text.lower() if lang == "en" else text.replace("요", "")  # 반말 변형
    # needs_question: 모델은 '문장이 모호한가'만 답한다. 템플릿 문장은 모호하지 않으므로 false.
    # '어지러움·두통·메스꺼움·피로인데 언제부터·언제 심해지는지 없음'은 서비스 코드(client.finish_symptom)가 계산한다.
    needs_q = False
    label = {"codes": sorted(codes), "onset": onset, "worse_when": worse, "severity": sev, "needs_question": bool(needs_q)}
    return text, label

def to_msg(text, label):
    return {"messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": text},
                         {"role": "assistant", "content": json.dumps(label, ensure_ascii=False)}]}

def main(n, ko_ratio):
    seen, rows = set(), []
    while len(rows) < n:
        lang = "ko" if random.random() < ko_ratio else "en"
        text, label = make(lang)
        if text in seen:
            continue
        seen.add(text)
        rows.append(to_msg(text, label))
    random.shuffle(rows)
    nv = max(50, n // 10)
    out = HERE / "symptoms"
    out.mkdir(exist_ok=True)
    with open(out / "valid.jsonl", "w") as f:
        for r in rows[:nv]:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out / "train.jsonl", "w") as f:
        for r in rows[nv:]:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (out / "schema.json").write_text(json.dumps({"codes": CODES, "onset": ONSET, "worse_when": WORSE, "system": SYSTEM}, ensure_ascii=False, indent=1))
    print(f"train {len(rows)-nv}  valid {nv}  -> {out}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=2400)
    ap.add_argument("--ko", type=float, default=0.65)
    a = ap.parse_args()
    main(a.n, a.ko)
