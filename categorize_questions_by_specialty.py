import json
import re

DATA_FILE = "data/questions.json"

# Rules for 12 Medical Specialties
SPECIALTY_RULES = [
    ("公衆衛生・医療倫理", [
        "公衆衛生", "地域保健", "医療法", "予防接種", "検診", "疫学", "診療所", "届出", "医師法", 
        "感染症法", "三次予防", "一次予防", "二次予防", "患者中心", "医療面接", "インフォームド・コンセント", 
        "倫理", "死亡診断書", "母子保健", "労働衛生", "介護保険", "高額療養費", "自己負担"
    ]),
    ("小児科", [
        "小児", "乳幼児", "新生児", "アデノイド", "アプガースコア", "麻疹", "水痘", "川崎病", 
        "思春期特発性側弯症", "先天性", "ファロー四徴", "乳児", "幼児", "学校検診", "早産"
    ]),
    ("産婦人科", [
        "妊娠", "妊婦", "分娩", "胎児", "月経", "子宮", "卵巣", "絨毛", "羊水", "切迫早産", 
        "子宮頸癌", "子宮体癌", "卵巣腫瘍", "無月経", "機能性月経困難症", "エストロゲン", "プロゲステロン"
    ]),
    ("循環器", [
        "心筋", "心不全", "心房細動", "頻拍", "心電図", "大動脈", "冠動脈", "心臓", "弁膜症", 
        "高血圧", "ショック", "除細動", "AED", "ベラパミル", "β遮断", "心筋梗塞", "狭心症"
    ]),
    ("呼吸器", [
        "肺", "気管支", "喘息", "気胸", "胸水", "無呼吸", "低酸素", "肺炎", "喀痰", "咳嗽", 
        "COPD", "結核", "呼吸不全", "EGFR", "間質性肺炎"
    ]),
    ("消化器", [
        "胃", "腸", "肝", "胆", "膵", "腹膜炎", "穿孔", "潰瘍", "イレウス", "消化管", 
        "食道", "便失禁", "ポリープ", "腹痛", "黄疸", "腹水", "内視鏡"
    ]),
    ("神経・精神", [
        "脳", "神経", "意識", "麻痺", "アルコール多飲", "うつ", "統合失調症", "認知症", 
        "パーキンソン", "てんかん", "頭痛", "脳梗塞", "脳出血", "ウェルニッケ", "睡眠症"
    ]),
    ("腎・尿路", [
        "腎", "尿", "結石", "ネフローゼ", "透析", "eGFR", "クレアチニン", "前立腺", "膀胱", "CKD"
    ]),
    ("内分泌・代謝", [
        "糖尿病", "甲状腺", "副腎", "コルチゾール", "インスリン", "Basedow", "アジソン", "クッシング", "痛風", "脂質異常"
    ]),
    ("血液・免疫・腫瘍", [
        "白血病", "貧血", "リンパ腫", "GVHD", "HIV", "抗体", "血小板", "凝固", "紫斑", "骨髄", "免疫不全"
    ]),
    ("整形・皮膚・感覚器", [
        "骨折", "脱臼", "皮疹", "皮膚", "側弯", "湿疹", "関節", "眼", "耳", "鼻", "コンパートメント", "皮膚筋炎"
    ]),
    ("救急・麻酔・総合", [
        "アナフィラキシー", "アドレナリン", "心停止", "救急", "中毒", "熱傷", "CPR", "外傷"
    ])
]

def categorize_question(q):
    text = q.get("question", "") + " " + " ".join(q.get("options", [])) + " " + (q.get("group_info", {}) or {}).get("stem", "")

    for spec_name, keywords in SPECIALTY_RULES:
        for kw in keywords:
            if kw in text:
                return spec_name
    return "総合臨床・その他"

def run():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    stats = {}
    for q in questions:
        spec = categorize_question(q)
        q["specialty"] = spec
        stats[spec] = stats.get(spec, 0) + 1

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print("Specialty distribution across all questions:")
    for k, v in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k}: {v}問")

if __name__ == "__main__":
    run()
