import fitz
import re

doc = fitz.open("downloads/tp260424-01e_01.pdf")
pages_text = []

for i in range(2, len(doc)):
    pages_text.append(doc[i].get_text())

full_text = "\n".join(pages_text)
lines = full_text.splitlines()

opt_chars = ['ａ', 'ｂ', 'ｃ', 'ｄ', 'ｅ']
opt_map = {c: idx for idx, c in enumerate(opt_chars)}

questions = []
current_q = None
current_opt_idx = -1

# Current active 連問 info
current_renmon_range = None
current_renmon_stem = ""

renmon_pattern = re.compile(r"次の文を読み[、\s]*(\d{1,3})[、\s]*(\d{1,3})?\s*の問いに答えよ")
q_num_pattern = re.compile(r"^\s*(\d{1,3})\s+(.*)")

for line in lines:
    line_str = line.strip()
    if not line_str:
        continue
        
    if "DKIX-" in line_str or "試験問題の数は" in line_str or "解答方法は" in line_str or "答案用紙" in line_str or "例1" in line_str or "例2" in line_str:
        continue

    # 1. Check for 連問 lead-in
    m_ren = renmon_pattern.search(line_str)
    if m_ren:
        if current_q:
            questions.append(current_q)
            current_q = None
            current_opt_idx = -1
            
        r_start = int(m_ren.group(1))
        r_end = int(m_ren.group(2)) if m_ren.group(2) else r_start
        current_renmon_range = (r_start, r_end)
        current_renmon_stem = line_str + "\n"
        continue

    # 2. Check for Options (ａ, ｂ, ｃ, ｄ, ｅ)
    is_opt = False
    for char, idx in opt_map.items():
        if line_str.startswith(char):
            is_opt = True
            opt_text = line_str[len(char):].strip()
            if current_q:
                if len(current_q["options"]) == idx:
                    current_q["options"].append(opt_text)
                elif len(current_q["options"]) < 5:
                    current_q["options"].append(opt_text)
                current_opt_idx = idx
            break

    if is_opt:
        continue

    # 3. Check for Question Start
    m_q = q_num_pattern.match(line_str)
    expected_num = len(questions) + 1

    if m_q and int(m_q.group(1)) == expected_num and not line_str.startswith("別冊") and not line_str.startswith("No"):
        if current_q:
            questions.append(current_q)
            
        is_renmon = False
        group_info = None
        
        if current_renmon_range and current_renmon_range[0] <= expected_num <= current_renmon_range[1]:
            is_renmon = True
            group_info = {
                "group_id": f"E{current_renmon_range[0]}-{current_renmon_range[1]}",
                "title": f"連問（問{current_renmon_range[0]}〜問{current_renmon_range[1]}）",
                "range": list(current_renmon_range),
                "stem": current_renmon_stem.strip()
            }

        current_q = {
            "num": expected_num,
            "is_renmon": is_renmon,
            "group_info": group_info,
            "question": m_q.group(2),
            "options": []
        }
        current_opt_idx = -1
        continue

    # 4. If we have not started question 1 yet, but saw a renmon header, append text to renmon_stem
    if current_q is None:
        if current_renmon_range:
            current_renmon_stem += line_str + "\n"
        continue

    # 5. Append remaining text to question stem or options
    if current_q:
        # If we are reading after Option E (current_opt_idx == 4) and encounter a new renmon header or page break, STOP appending to Option E!
        if current_opt_idx == 4 and ("次の文を読み" in line_str or "別冊" in line_str):
            continue
            
        if current_opt_idx == -1:
            current_q["question"] += "\n" + line_str
        elif 0 <= current_opt_idx < len(current_q["options"]):
            current_q["options"][current_opt_idx] += " " + line_str

if current_q:
    questions.append(current_q)

print(f"Parsed EXACT {len(questions)} questions for Block E.")

for q in questions:
    if q["num"] in [43, 44, 45, 46]:
        print(f"\n=== Question {q['num']} ===")
        print("Is Renmon:", q.get("is_renmon"))
        if q.get("group_info"):
            print("Renmon Stem:", repr(q["group_info"]["stem"][:100]))
        print("Question Text:", repr(q["question"]))
        print("Options:", q["options"])
