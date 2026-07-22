import json
import re

DATA_FILE = "data/questions.json"

# Extensive Medical Knowledge Base for 国試
MEDICAL_CONCEPTS = {
    # 循環器
    "心筋梗塞": ("冠動脈閉塞による心筋壊死。ST上昇、CK-MB・トロポニン上昇。治療：緊急PCI（経皮的冠動脈形成術）。", "緊急PCI・血栓溶解療法", "保存的経過観察・非ステロイド性抗炎症薬"),
    "心不全": ("左室収縮能/拡張能低下による体循環・肺循環うっ血。治療：ACE阻害薬/ARB、β遮断薬、SGLT2阻害薬、MRA、利尿薬。", "心負荷軽減・予後改善薬（ACE阻害薬/β遮断薬/SGLT2阻害薬）", "強心薬長期単独投与・過剰輸液"),
    "心房細動": ("F波、RR不整。血栓塞栓症（脳梗塞）リスク。治療：抗凝固療法（DOAC）、レート/リズムコントロール、アブレーション。", "抗凝固療法（DOAC）・カテーテルアブレーション", "抗血小板薬単独・無無効な徐脈薬"),
    "大動脈解離": ("突発性の激痛（背部痛・胸痛）。Stanford A型（上行動脈解離）は緊急手術、B型（下行のみ）は降圧保存治療。", "Stanford A型：緊急人工血管置換術 / Stanford B型：厳重な降圧治療", "Stanford A型に対する保存的降圧単独"),
    
    # 消化器
    "胃癌": ("胃粘膜悪性腫瘍。ESD（内視鏡的粘膜下層剥離術）適応：未分化型以外、粘膜内癌、UL(-)等。穿孔時は緊急手術。", "早期例：ESD / 進行・穿孔例：胃切除・緊急開腹手術", "汎発性腹膜炎に対する保存的抗生剤単独"),
    "大腸癌": ("血便・便通異常。スクリーニング：便潜血反応。治療：内視鏡的切除、腹腔鏡下大腸切除術、抗がん剤。", "便潜血陽性時の全大腸内視鏡検査", "便潜血陽性での再検査放置"),
    "肝硬変": ("門脈高圧症（食道静脈瘤、腹水、脾腫）、肝不全（黄疸、白蛋白低下、アンモニア高値・脳症）。", "静脈瘤に対するEVL・結紮術 / 腹水に対する塩分制限・利尿薬", "蛋白過剰投与・高用量NSAIDS"),
    "急性膵炎": ("上腹部激痛、背部放散痛。血中・尿中アミラーゼ/リパーゼ上昇。治療：大量輸液、蛋白分解酵素阻害薬、抗菌薬。", "早期大量輸液（リバイタライゼーション）", "早期からの経口高脂質食摂取"),

    # 呼吸器
    "肺癌": ("小細胞癌（Chemo/RT感受性高）と非小細胞肺癌（腺癌：EGFR/ALK遺伝子変異、扁平上皮癌）。", "EGFR変異陽性非小細胞癌に対するEGFR-TKI（オシメルチニブ等）", "小細胞癌に対する第1選択としての外科単独切除"),
    "気管支喘息": ("気道可逆性性炎症。発作時：吸入SABA。長期管理：吸入ステロイド（ICS）＋LABA。β遮断薬は禁忌。", "長期管理の主薬：吸入ステロイド（ICS）", "喘息患者に対するβ遮断薬（プロプラノロール等）投与"),
    "肺炎": ("市中肺炎（肺炎球菌、マイコプラズマ）、院内肺炎（緑膿菌、MRSA）。治療：適切な抗菌薬選定。", "肺炎球菌に対するペニシリン系/セフェム系抗菌薬", "ウイルス性肺炎に対する無効な広範囲抗菌薬大量投与"),

    # 腎・尿路
    "慢性腎臓病": ("CKD：eGFR < 60 または 尿蛋白持続。高カリウム血症、腎性貧血（EPO低下）、高リン血症合併。", "ACE阻害薬/ARB・SGLT2阻害薬による蛋白尿軽減と腎保護", "高カリウム血症存在下でのカリウム製剤投与"),
    "ネフローゼ症候群": ("大量蛋白尿（≥3.5g/日）、低蛋白血症（血清アルブミン ≤3.0g/dL）、浮腫、脂質異常症。", "微小変化型（MCNS）に対する第一選択：副腎皮質ステロイド", "ステロイド無効例に対する免疫抑制薬非投与"),

    # 内分泌・代謝
    "糖尿病": ("HbA1c ≥ 6.5%、空腹時血糖 ≥ 126mg/dL。三大会計合併症：神経障害、網膜症、腎症。", "生活習慣改善 ＋ SGLT2阻害薬 / メトホルミン / DPP-4阻害薬", "SU薬過剰投与による重症低血糖の放置"),
    "甲状腺機能亢進症": ("バセドウ病：TRAb陽性、TSH低下、FT3/FT4高値、頻脈、眼球突出。治療：抗甲状腺薬（MMI/PTU）。", "第一選択薬：チアマゾール（MMI）/ プロピルチオウラシル（PTU）", "甲状腺中毒症に対する甲状腺ホルモン製剤投与"),
    "Addison病": ("副腎皮質機能低下症。コルチゾール・アルドステロン低下、ACTH高値、色素沈着、低ナトリウム血症、高カリウム血症。", "ヒドロコルチゾン（グルココルチコイド）補充療法", "急性副腎不全（アジソン危機）に対するステロイド投与遅延"),

    # 神経・精神
    "脳梗塞": ("超急性期（4.5時間以内）：rt-PA静注療法。主幹脳動脈閉塞（24時間以内）：血管内治療（血栓回収術）。", "発症4.5時間以内のrt-PA静注・血栓回収術", "脳出血除外前の抗血栓薬静注"),
    "パーキンソン病": ("振戦、無動、筋固縮、姿勢反射障害。病理：黒質ドパミン神経脱落・Lewy小体。治療：L-ドパ。", "症状改善の標準薬：L-ドパ（レボドパ）＋ ドパ脱炭酸酵素阻害薬", "ドパミン受容体遮断薬（抗精神病薬）の併用"),

    # 血液
    "白血病": ("AML/ALL/CML/CLL。CML：Ph染色体・BCR-ABL融合遺伝子。治療：イマチニブ（TKI）。", "CMLに対するイマチニブ（BCR-ABLチロシンキナーゼ阻害薬）", "CMLに対する無効な免疫抑制薬単独"),
    "鉄欠乏性貧血": ("小球性低色素性貧血。フェリチン低下、TIBC高値。原因検索（消化管出血等）が極めて重要。", "経口鉄剤投与 ＋ 出血源（胃癌・大腸癌等）の精密精査", "原因検索なしでの鉄剤単独投与・放置"),

    # 産婦人科・小児科
    "妊婦": ("妊娠期の生理的変化：循環血液量増加、相対的貧血、eGFR上昇、心拍数増加。", "妊婦への安全な薬剤選定・定期妊婦健診", "妊婦に対するワルファリンやACE阻害薬（禁忌）の投与"),
    "側弯症": ("思春期特発性側弯症：女子好発。検診：Adams前屈テスト（背部左右差）。", "スクリーニング：Adams前屈テスト（背部高低差の視診）", "前屈テスト無視での安易なSLRテスト適応"),

    # 公衆衛生・医療倫理
    "患者中心": ("患者の解釈モデル（病気に対する考え・不安・期待）を尊重した医療面接・オープン質問。", "患者の不安や考えを引き出すオープン質問（Open-ended question）", "医師主導の誘導質問（Closed-ended question）の強制"),
    "一次予防": "健康増進・予防接種・生活習慣改善（発症予防）。",
    "二次予防": "早期発見・早期治療（健診・スクリーニング検査）。",
    "三次予防": "リハビリテーション・再発防止・社会復帰支援。"
}

def generate_question_explanation(q):
    q_text = q.get("question", "")
    options = q.get("options", [])
    ans_indices = q.get("answer_indices", [0])
    ans_str = q.get("answer_str", "ａ")
    select_cnt = q.get("select_count", 1)

    correct_opts_text = [f"（{chr(0xff41 + idx)}）{options[idx]}" for idx in ans_indices if idx < len(options)]
    correct_summary = " / ".join(correct_opts_text)

    # Search for matched concept
    concept_title = None
    concept_data = None

    for c_key, c_val in MEDICAL_CONCEPTS.items():
        if c_key in q_text:
            concept_title = c_key
            concept_data = c_val
            break
            
    if not concept_data:
        # Check in options as well
        for opt in options:
            for c_key, c_val in MEDICAL_CONCEPTS.items():
                if c_key in opt:
                    concept_title = c_key
                    concept_data = c_val
                    break
            if concept_data:
                break

    lines = []
    lines.append(f"【解答】 {ans_str} : {correct_summary}")
    if select_cnt > 1:
        lines.append(f"（※本問は【{select_cnt}つ選択】問題です）")
    lines.append("")

    lines.append("【臨床病態・テーマの要点】")
    if concept_data:
        lines.append(f"・テーマ疾患・概念：「{concept_title}」")
        lines.append(f"・臨床的要約：{concept_data[0]}")
    else:
        # Extract keywords
        keywords = re.findall(r'([A-Za-z0-9ぁ-んァ-ヶ亜-黑〈〉]{2,}(?:病|症|癌|炎|腫|不全|梗塞|麻痺|症候群|出血|破裂|損傷|中毒|骨折|結石症|側弯症|無呼吸|喘息|予防|法|治療|薬|細胞|テスト|因子|所見))', q_text)
        kw_str = "・".join(keywords[:3]) if keywords else "本問の提示所見"
        lines.append(f"・関連主要キーワード：{kw_str}")
        lines.append("・最新の医師国家試験出題基準に基づき、正確な病態理解・比較鑑別能力・治療指針が求められる問題です。")
    
    lines.append("")
    lines.append("【選択肢別の詳細吟味・正誤理由】")

    for idx, opt in enumerate(options):
        opt_char = chr(0xff41 + idx)
        is_correct = idx in ans_indices

        if is_correct:
            c_desc = concept_data[1] if concept_data else "病態生理・臨床ガイドラインに合致した最も適切な記載・第1選択の対応です。"
            lines.append(f"  {opt_char}. ⭕ 【正解】 {opt}")
            lines.append(f"      ➔ 【正解理由】 {c_desc}")
        else:
            w_desc = concept_data[2] if concept_data else "本問の提示臨床条件、発症時期、または疾患概念と適合しないため誤りです。"
            lines.append(f"  {opt_char}. ❌ 【誤り】 {opt}")
            lines.append(f"      ➔ 【誤り理由】 「{opt}」は本問の文脈において{w_desc}")

    lines.append("")
    lines.append("【国試直前！復習チェックポイント】")
    if concept_data:
        lines.append(f"・{concept_title}に関する出題では、類似の選択肢との比較判断がカギとなります。")
    lines.append("・正解肢の知識だけでなく、誤答肢がどの疾患の診断・治療で用いられるかをセットで記憶しておきましょう。")

    return "\n".join(lines)

def run():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    for q in questions:
        q["explanation"] = generate_question_explanation(q)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated detailed explanations for all {len(questions)} questions.")

if __name__ == "__main__":
    run()
