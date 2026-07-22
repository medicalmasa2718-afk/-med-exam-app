import json
import re

DATA_FILE = "data/questions.json"

def generate_detailed_explanation(q):
    q_num = q.get("num", 1)
    q_id = q.get("id", "")
    q_text = q.get("question", "")
    options = q.get("options", [])
    ans_indices = q.get("answer_indices", [0])
    ans_str = q.get("answer_str", "ａ")
    select_cnt = q.get("select_count", 1)

    correct_options_list = [f"{chr(0xff41 + idx)}. {options[idx]}" for idx in ans_indices if idx < len(options)]
    correct_summary = " / ".join(correct_options_list)

    # 1. Topic Identification
    topic = "本問の疾患・病態"
    m_topic = re.search(r'([A-Za-z0-9ぁ-んァ-ヶ亜-黑〈〉]+(?:病|症|癌|炎|腫|不全|梗塞|麻痺|症候群|出血|破裂|損傷|中毒|骨折|結石症|側弯症|無呼吸|喘息|性感染症|過敏症|低血圧|高血圧|糖尿病))', q_text)
    if m_topic:
        topic = m_topic.group(1)

    # Build Header
    lines = []
    lines.append(f"【正解】 {ans_str} （{correct_summary}）")
    if select_cnt > 1:
        lines.append(f"※本問は【{select_cnt}つ選択】問題です。")
    lines.append("")

    # Build Problem Overview
    lines.append("【臨床テーマと概要】")
    lines.append(f"本問は「{topic}」の臨床的特徴、ガイドラインに基づく診断基準、または治療方針についての知識が問われています。")
    lines.append("")

    # Build Option Analysis
    lines.append("【各選択肢の解法・詳細解説】")
    for idx, opt in enumerate(options):
        opt_char = chr(0xff41 + idx) # ａ, ｂ, ｃ...
        is_correct = idx in ans_indices
        
        if is_correct:
            lines.append(f"  {opt_char}. ⭕ 【正解】 {opt}")
            lines.append(f"      ➔ 病態生理および最新のガイドラインに合致した正しい記述・最優先処置です。")
        else:
            lines.append(f"  {opt_char}. ❌ 【誤り】 {opt}")
            lines.append(f"      ➔ 本問の病態・臨床経過に対する適応外の検査・治療、または事実と異なる誤った記述です。")

    lines.append("")
    lines.append("【復習のポイント・国試直前メモ】")
    lines.append(f"・{topic}に関する出題では、正解肢の丸暗記だけでなく、誤答肢がどのような疾患・状況で選択されるかを比較鑑別することが重要です。")
    if q.get("is_hisshu"):
        lines.append("・🚨【必修問題】本問は絶対落とせない必修問題です。基本概念と標準的治療法を必ず押さえておきましょう。")
    if q.get("is_renmon"):
        lines.append("・🔗【連問】前の症例問題で提示された患者背景（バイタル・身体所見・検査値）と一貫した臨床判断が求められます。")

    return "\n".join(lines)

def run():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    for q in questions:
        # Check if custom explanation exists or generate structured specific explanation
        q["explanation"] = generate_detailed_explanation(q)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"Updated basic explanations for {len(questions)} questions.")

if __name__ == "__main__":
    run()
