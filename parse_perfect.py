import fitz
import re

doc = fitz.open("downloads/tp260424-01a_01.pdf")
pages_text = []

# Exclude cover pages (0 and 1)
for i in range(2, len(doc)):
    pages_text.append(doc[i].get_text())

full_text = "\n".join(pages_text)
lines = full_text.splitlines()

questions = []
current_q = None
current_opt_idx = -1

# Full-width a-e to 0-4
opt_chars = ['ａ', 'ｂ', 'ｃ', 'ｄ', 'ｅ']
opt_map = {c: idx for idx, c in enumerate(opt_chars)}

q_num_pattern = re.compile(r"^\s*(\d{1,3})\s+(.*)")

for line in lines:
    line_str = line.strip()
    if not line_str:
        continue
        
    # Ignore headers/footers
    if "DKIX-" in line_str or "試験問題の数は" in line_str or "解答方法は" in line_str or "答案用紙" in line_str or "例1" in line_str or "例2" in line_str:
        continue

    # Check if this line is an option label (ａ, ｂ, ｃ, ｄ, ｅ)
    # Could be "ａ　緊急手術" or just "ａ"
    is_option_line = False
    for char, idx in opt_map.items():
        if line_str.startswith(char):
            is_option_line = True
            opt_content = line_str[len(char):].strip()
            
            if current_q:
                # Add option
                if len(current_q["options"]) == idx:
                    current_q["options"].append(opt_content)
                elif len(current_q["options"]) < 5:
                    current_q["options"].append(opt_content)
                current_opt_idx = idx
            break

    if is_option_line:
        continue

    # Check if question start
    m_q = q_num_pattern.match(line_str)
    if m_q and current_opt_idx in [-1, 4]: # Only start new question if not in middle of options A-D
        q_num = int(m_q.group(1))
        if 1 <= q_num <= 75:
            if current_q and len(current_q["options"]) >= 2:
                questions.append(current_q)
            
            current_q = {
                "num": q_num,
                "question": m_q.group(2),
                "options": []
            }
            current_opt_idx = -1
            continue

    # Otherwise append text to question or option
    if current_q:
        if current_opt_idx == -1:
            current_q["question"] += "\n" + line_str
        elif current_opt_idx >= 0 and current_opt_idx < len(current_q["options"]):
            current_q["options"][current_opt_idx] += " " + line_str

if current_q and len(current_q["options"]) >= 2:
    questions.append(current_q)

# Deduplicate by num
unique_q = {q["num"]: q for q in questions}
sorted_q = sorted(unique_q.values(), key=lambda x: x["num"])

print(f"Parsed EXACTLY {len(sorted_q)} / 75 questions for Block A!")
for q in sorted_q[:5]:
    print(f"--- Q{q['num']} ---")
    print("Question:", repr(q['question'][:60]))
    print("Options:", q['options'])
