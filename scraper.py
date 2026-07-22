"""
医師国家試験 第120回 問題PDFスクレーパー
厚生労働省公式PDF → questions.json
"""
import os
import re
import json
import urllib.parse
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF

BASE_URL   = "https://www.mhlw.go.jp/seisakunitsuite/bunya/kenkou_iryou/iryou/topics/tp260424-01.html"
SEITOU_URL = "https://www.mhlw.go.jp/seisakunitsuite/bunya/kenkou_iryou/iryou/topics/dl/tp260424-01seitou.pdf"
DOWNLOAD_DIR = "downloads"
IMAGE_DIR    = "images"
DATA_DIR     = "data"
DATA_FILE    = "data/questions.json"

for d in (DOWNLOAD_DIR, IMAGE_DIR, DATA_DIR):
    os.makedirs(d, exist_ok=True)

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

BLOCK_INFO = {
    "A": ("一般問題 (ブロック A)", False, 75),
    "B": ("必修問題 (ブロック B)", True,  50),
    "C": ("臨床問題 (ブロック C)", False, 75),
    "D": ("一般問題 (ブロック D)", False, 75),
    "E": ("必修問題 (ブロック E)", True,  50),
    "F": ("臨床問題 (ブロック F)", False, 75),
}

OPT_CHARS = ['ａ', 'ｂ', 'ｃ', 'ｄ', 'ｅ']
OPT_IDX   = {c: i for i, c in enumerate(OPT_CHARS)}
CHAR_TO_ANSIDX = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4}


# ─────────────────────────────────────────────────────────────────────────────
def download(url):
    fname = os.path.basename(urllib.parse.urlparse(url).path)
    path  = os.path.join(DOWNLOAD_DIR, fname)
    if not os.path.exists(path):
        r = requests.get(url, headers=HTTP_HEADERS)
        with open(path, "wb") as f:
            f.write(r.content)
    return path


def clean(text):
    if not text:
        return ""
    # 別冊参照ラベルを除去
    text = re.sub(r"別\s*冊\s*No\.[\s\u3000\d①-⑳Ａ-ＦA-F～\-、・～]*", "", text)
    text = re.sub(r"DKIX-\S*", "", text)
    return re.sub(r"\s+", " ", text).strip()


# ─────────────────────────────────────────────────────────────────────────────
def parse_answer_keys(pdf_path):
    doc  = fitz.open(pdf_path)
    text = "\n".join(p.get_text() for p in doc)
    keys = {}
    for m in re.finditer(r"([A-F])(\d{3})\s*\n?\s*([A-E]+)", text):
        block, num, ans = m.group(1), int(m.group(2)), m.group(3)
        k       = f"{block}{num}"
        indices = [CHAR_TO_ANSIDX[c] for c in ans if c in CHAR_TO_ANSIDX]
        keys[k] = {"indices": indices, "count": len(indices), "str": ans}
    print(f"[ANSWER] {len(keys)} keys parsed")
    return keys


# ─────────────────────────────────────────────────────────────────────────────
def parse_supplement_images(pdf_path, block_letter):
    doc     = fitz.open(pdf_path)
    pattern = re.compile(r"[（\(]\s*([A-ZＡ-Ｚa-zａ-ｚ])\s*問[題?\s\u3000]*([0-9０-９\s\u3000～〜、,・\-]+)[）\)]")
    mapped  = {}
    for pi in range(len(doc)):
        page = doc[pi]
        hits = pattern.findall(page.get_text())
        if not hits:
            continue
        pix = page.get_pixmap(dpi=150)
        for b_char, q_raw in hits:
            b = b_char.upper()
            if 'Ａ' <= b <= 'Ｆ':
                b = chr(ord(b) - ord('Ａ') + ord('A'))
            if b != block_letter:
                continue

            q_raw_norm = q_raw.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            q_numbers = []
            range_m = re.search(r"(\d{1,3})\s*[～〜\-]\s*(\d{1,3})", q_raw_norm)
            if range_m:
                start_n, end_n = int(range_m.group(1)), int(range_m.group(2))
                q_numbers.extend(range(start_n, end_n + 1))
            else:
                for num_str in re.findall(r"\d{1,3}", q_raw_norm):
                    q_numbers.append(int(num_str))

            fname = f"block_{block_letter}_p{pi+1}.png"
            fpath = os.path.join(IMAGE_DIR, fname)
            if not os.path.exists(fpath):
                pix.save(fpath)
            rel = f"images/{fname}"

            for qn in set(q_numbers):
                mapped.setdefault(str(qn), [])
                if rel not in mapped[str(qn)]:
                    mapped[str(qn)].append(rel)

    print(f"[IMAGE]  Block {block_letter}: {len(mapped)} questions have images")
    return mapped



# ─────────────────────────────────────────────────────────────────────────────
def parse_questions(pdf_path, block, answer_keys, img_map):
    """
    PDFページ構造:
      page0: 表紙（DKIX + 注意事項）
      page1+: 問題ページ
        ・先頭行: DKIX-xxx (ヘッダー)
        ・全角スペースのみ行
        ・ページ番号（単独の1〜2桁数字: 1, 2, 3...）
        ・以降: 問題行 (N テキスト...) or 選択肢行 (ａ テキスト...)

    問題番号行のパターン:
      A) "N テキスト"  - 番号と本文が同一行
      B) "N"          - 番号のみの行（次の行が本文の続き）
    """
    category, is_hisshu, max_q = BLOCK_INFO[block]
    doc = fitz.open(pdf_path)

    # 全ページの全ラインを収集
    all_raw = []
    for pi in range(len(doc)):
        for raw in doc[pi].get_text("text", sort=True).splitlines():
            all_raw.append(raw)


    # ── 1次フィルタ: 明らかなスキップ行を除去 ────────────────────
    filtered = []
    for raw in all_raw:
        s = raw.strip()
        if not s:
            continue
        if s.startswith("DKIX-"):
            continue
        if re.fullmatch(r"[\u3000\s]+", s):
            continue
        # 表紙の固定文言
        skip_kw = ["指示があるまで", "試験問題の数は", "解答方法は次", "答案用紙",
                   "正解は「", "↓", "→", "◎指示", "令和8年", "令和 8 年",
                   "13 時", "（令和", "注\u3000意\u3000事\u3000項",
                   "選択肢を1 つ選び", "選択肢を2 つ選び",
                   "答案用紙①", "答案用紙②"]
        if any(kw in s for kw in skip_kw):
            continue
        filtered.append(s)

    # ── 問題セクションの開始点を検出 ────────────────────────────
    # 本文問題 1 から始まる箇所を探す
    start_idx = 0
    for i, s in enumerate(filtered):
        m = re.match(r"^1[\s\u3000]+(\S.*)$", s)
        if m and s[0] not in OPT_IDX:
            text_after = m.group(1)
            # 表紙の例題や注意事項・マークシート数字列でないことを確認
            skip_phrases = ["医師免許", "保健所", "つ選び", "答案用紙", "例", "指示", "記入", "マーク", "①", "②", "数字"]
            if any(p in text_after for p in skip_phrases) or re.match(r"^\d", text_after):
                continue
            start_idx = i
            break



    lines = filtered[start_idx:]



    # ── 状態機械でパース ─────────────────────────────────────────
    questions       = []
    current_q       = None
    current_opt_idx = -1  # -1: 選択肢前, 0-4: 最後に読んだ選択肢インデックス
    pending_q_num   = None  # 問題番号のみ行を読んだ後、次行を本文として使う

    # 連問状態
    renmon_range      = None
    renmon_stem_lines = []
    collecting_renmon = False

    RE_RENMON = re.compile(r"次の文を読み[、,\s\u3000]*(\d{1,3})[^を\d]*(\d{1,3})\s*の問い")

    def save_q():
        nonlocal current_q, current_opt_idx, pending_q_num
        if current_q is None:
            return
        q = current_q
        q["question"] = clean(q["question"])
        cleaned_opts = []
        for o in q["options"]:
            co = clean(o)
            # 末尾にくっついた他問題本文や単独ページ番号を除去
            co = re.sub(r"[\s\u3000]+\d{1,3}$", "", co).strip()
            co = re.sub(r"[\s\u3000]+(?:慣はなく|尿量|10 歳|40 歳|解答：|①|②|③).*$", "", co).strip()
            if co:
                cleaned_opts.append(co)
        q["options"] = cleaned_opts

        if q["question"]:
            questions.append(q)
            found_q_nums.add(q["num"])
        current_q       = None
        current_opt_idx = -1
        pending_q_num   = None



    # 単位表記そのもので始まる行（例: "%", "mg/dL", "mEq/L" 等）を問題番号と誤認しないための正規表現
    SKIP_UNIT_RE = re.compile(r"^(?:%|％|mm|cm|mg|g|mL|mEq|Torr|kg|mOsm|gCr)\b", re.IGNORECASE)




    def build_q(num, text_start):
        key      = f"{block}{num}"
        ans_info = answer_keys.get(key, {"indices": [0], "count": 1, "str": "A"})
        is_renmon = bool(renmon_range and renmon_range[0] <= num <= renmon_range[1])
        group_info = None
        if is_renmon:
            group_info = {
                "group_id": f"{block}{renmon_range[0]}-{renmon_range[1]}",
                "title":    f"連問（問{renmon_range[0]}〜問{renmon_range[1]}）",
                "range":    list(renmon_range),
                "stem":     clean(" ".join(renmon_stem_lines))
            }
        return {
            "id":            f"問{num} (ブロック {block})",
            "num":           num,
            "category":      category,
            "is_hisshu":     is_hisshu,
            "is_renmon":     is_renmon,
            "group_info":    group_info,
            "question":      text_start,
            "image_urls":    img_map.get(str(num), []),
            "options":       [],
            "answer_indices": ans_info["indices"],
            "select_count":  ans_info["count"],
            "answer_str":    ans_info["str"],
            "explanation":   "",
            "mnemonic":      None
        }

    # 正答キーに存在する問題番号の集合（ページ番号との区別に使用）
    valid_q_nums = set()
    for k in answer_keys:
        if k.startswith(block):
            try:
                valid_q_nums.add(int(k[len(block):]))
            except ValueError:
                pass
    if not valid_q_nums:
        # フォールバック: 全問題番号を有効とする
        valid_q_nums = set(range(1, max_q + 1))

    expected = 1  # 次に来るべき問題番号（連問ジャンプ用にも使用）
    found_q_nums: set = set()  # 既に取得した問題番号（ページ番号との区別用）

    for line in lines:
        # ── 連問ヘッダー ──────────────────────────────────────────
        if "次の文を読み" in line:
            m = RE_RENMON.search(line)
            if m:
                save_q()
                pending_q_num     = None
                renmon_range      = (int(m.group(1)), int(m.group(2)))
                renmon_stem_lines = [line]
                collecting_renmon = True
                current_opt_idx   = -1
                # 連問の開始問題番号にexpectedをジャンプ
                expected          = renmon_range[0]
                continue

        # ── 選択肢行 ──────────────────────────────────────────────
        if line and line[0] in OPT_IDX and current_q is not None:
            collecting_renmon = False
            pending_q_num     = None
            opt_char = line[0]
            opt_text = line[1:].lstrip('\u3000 ').strip()
            idx = OPT_IDX[opt_char]
            if idx == len(current_q["options"]):
                current_q["options"].append(opt_text)
                current_opt_idx = idx
            elif idx < len(current_q["options"]):
                pass  # 重複スキップ
            else:
                # 間に飛びがある場合はそのまま追加
                current_q["options"].append(opt_text)
                current_opt_idx = idx
            continue

        # ── pending_q_num処理: 前の行が番号のみだった → 今の行が本文 ─
        if pending_q_num is not None:
            captured_num  = pending_q_num
            pending_q_num = None

            # 次の行が「M テキスト」の形で始まるか確認
            m_check = re.match(r"^(\d{1,3})[\s\u3000]+(.+)$", line)
            if m_check:
                next_num = int(m_check.group(1))
                # 年齢表記や医療測定値（9 歳、50 歳、147 cm、38 ℃等）の場合は問題番号ではなく問題本文頭
                is_age_or_value = bool(re.match(r"^\d{1,3}[\s\u3000]*(?:歳|ヶ月|か月|日|時間|分|度|cm|kg|g|mL|mg|mEq|Torr|%|％|万|分|回)", line))

                if next_num == captured_num or is_age_or_value:
                    # N単独行 + 「N テキスト」または「N 歳の...」: captured_num が本来の問題番号
                    save_q()
                    collecting_renmon = False
                    current_q       = build_q(captured_num, line)
                    current_opt_idx = -1
                    found_q_nums.add(captured_num)
                    continue
                elif next_num in valid_q_nums and next_num not in found_q_nums:
                    # next_numが有効な問題番号 → captured_numはページ番号だった
                    # → このlineを通常の問題番号検出に委ねる（fall through）
                    pass
                elif next_num < captured_num:
                    save_q()
                    collecting_renmon = False
                    current_q       = build_q(captured_num, line)
                    current_opt_idx = -1
                    found_q_nums.add(captured_num)
                    continue
                else:
                    pass
            elif not re.match(r"^別\s*冊", line) and line[0:1] not in OPT_IDX:
                # 次の行が数字で始まらない通常テキスト → pendingが正しい問題番号
                save_q()
                collecting_renmon = False
                current_q       = build_q(captured_num, line)
                current_opt_idx = -1
                found_q_nums.add(captured_num)
                continue
            else:
                # 番号行の後に選択肢または別冊ラベル → 番号のみで問題文空
                save_q()
                current_q       = build_q(captured_num, "")
                current_opt_idx = -1
                found_q_nums.add(captured_num)
                # このlineを再処理するため fall through


        # ── 問題番号の検出 ────────────────────────────────────────
        # マークシート入力指示文（解答：①、① ②等）が現れた場合、選択肢なし問題の本文完了とみなす
        if current_q is not None and current_opt_idx == -1:
            if re.search(r"解答：|①\s*②|①\s*\．\s*②|mOsm/kgH2O|g/gCr|BMI", line):
                current_opt_idx = 99  # 本文完了

        # 問題文を読んでいる途中（選択肢前）は、インライン「N テキスト」を問題番号として
        # 誤認識しない（問題文中に数字が含まれるため）
        reading_stem = (current_q is not None and current_opt_idx == -1)

        m_inline = re.match(r"^(\d{1,3})[\s\u3000]+(.+)$", line) if not reading_stem else None
        m_alone  = re.match(r"^(\d{1,3})$", line)

        if m_inline:
            cand_num = int(m_inline.group(1))
            cand_txt = m_inline.group(2).strip()

            # 連問の症例本文を収集中の場合、連問最初の問題番号 (renmon_range[0]) 以外は問題番号とみなさない
            is_valid_renmon_start = True
            if collecting_renmon and renmon_range:
                if cand_num != renmon_range[0]:
                    is_valid_renmon_start = False

            if is_valid_renmon_start and cand_num in valid_q_nums and cand_num not in found_q_nums and not SKIP_UNIT_RE.match(cand_txt):
                if collecting_renmon and renmon_range and cand_num == renmon_range[0]:
                    collecting_renmon = False
                save_q()
                current_q       = build_q(cand_num, cand_txt)
                current_opt_idx = -1
                found_q_nums.add(cand_num)
                continue

        if m_alone:
            cand_num = int(m_alone.group(1))
            # 現在パース中の問題番号以下の数字はページ番号（p55等）なので問題番号とみなさない
            if current_q is not None and cand_num <= current_q["num"]:
                pass
            elif collecting_renmon and renmon_range and cand_num != renmon_range[0]:
                pass
            elif cand_num in valid_q_nums and cand_num not in found_q_nums:
                # 問題番号のみ行（次行が問題文）
                if collecting_renmon and renmon_range and cand_num == renmon_range[0]:
                    collecting_renmon = False
                pending_q_num = cand_num
                continue



        # ── その他のテキスト ──────────────────────────────────────
        if collecting_renmon:
            renmon_stem_lines.append(line)
            continue

        if current_q is not None:
            # 別冊ラベルはスキップ
            if re.match(r"^別\s*冊|^No\.\s*\d", line):
                continue
            if current_opt_idx in (-1, 99):
                # 問題文の続き（または計算問題のマーク入力文）
                current_q["question"] += "\n" + line
            else:
                # 選択肢の続き

                # 次の問題番号と誤認されないようにチェック
                if re.match(r"^(\d{1,3})[\s\u3000]*$", line):
                    cand = int(re.match(r"^(\d{1,3})", line).group(1))
                    if cand == expected:
                        continue  # 次の問題番号なのでスキップ
                if not re.match(r"^別\s*冊|^No\.\s*\d|^解答：|^\d{1,3}[\s\u3000]*$|^\d[\s\u3000]+\d[\s\u3000]+\d", line):
                    # 他の問題番号や「40 歳の男性...」のような記述問題本文で始まる行も選択肢に追加しない
                    m_other_q = re.match(r"^(\d{1,3})[\s\u3000]+(.+)$", line)
                    if m_other_q:
                        cand_n = int(m_other_q.group(1))
                        if cand_n > current_q["num"] or cand_n in valid_q_nums:
                            continue
                    if 0 <= current_opt_idx < len(current_q["options"]):
                        current_q["options"][current_opt_idx] += " " + line




    save_q()

    valid = [q for q in questions if q["num"] <= max_q]
    print(f"[PARSE]  Block {block}: {len(valid)}/{max_q} questions")
    return valid


# ─────────────────────────────────────────────────────────────────────────────
def generate_explanation(q):
    opts    = q.get("options", [])
    indices = q.get("answer_indices", [0])
    ans_str = q.get("answer_str", "A")
    cnt     = q.get("select_count", 1)

    trans_map = str.maketrans("ABCDE", "ａｂｃｄｅ")
    ans_str_zen = ans_str.translate(trans_map)
    q["answer_str"] = ans_str_zen

    lines = []
    lines.append(f"【正解】 {ans_str_zen}")
    if cnt > 1:
        lines.append(f"💡 ※この問題は {cnt} つ選択する複数選択問題です。")
    lines.append("")

    if opts:
        lines.append("【各選択肢の正誤と解説】")
        for i, opt in enumerate(opts):
            is_cor = (i in indices)
            label = chr(ord('ａ') + i)
            if is_cor:
                lines.append(f"  {label}. ⭕ 【正解肢】 {opt}")
                lines.append(f"      ➔ 本問の病態・ガイドラインにおいて最も適切な選択肢です。")
            else:
                lines.append(f"  {label}. ❌ 【誤り肢】 {opt}")
                lines.append(f"      ➔ 本問の提示臨床所見または診断基準に適合しないため誤りです。")
        lines.append("")

    lines.append("【臨床・解答の要点】")
    q_txt = q.get("question", "")
    if "画像" in q_txt or "エックス線" in q_txt or "CT" in q_txt or "MRI" in q_txt or "心電図" in q_txt or q.get("image_urls"):
        lines.append("・【画像・検査所見】提示された検査画像（レントゲン・CT・MRI・心電図・写真）および血液・生化学検査値の特徴的所見から病態を特定します。")
    if "正しいのはどれか" in q_txt or "適切なのはどれか" in q_txt:
        lines.append("・【治療・対応方針】最新の臨床診療ガイドラインに基づき、第1選択とされる検査・処置・初期対応・薬物治療が正解となります。")
    elif "誤っているのはどれか" in q_txt or "含まれないのはどれか" in q_txt:
        lines.append("・【禁忌・除外診断】本疾患において非適応または禁忌（施行してはならない処置）とされる項目、あるいは定義に含まれない項目を選択します。")
    else:
        lines.append("・【診断・病態生理】臨床経過、主訴、身体診察所見（バイタルサイン・聴診・触診等）から最も考えられる疾患・病態を選定します。")

    if q.get("is_hisshu"):
        lines.append("・【必修重要事項】医師として不可欠な医療倫理・公衆衛生・感染対策・基本手技・救急対応に関する必修知識です。")

    return "\n".join(lines)




# ─────────────────────────────────────────────────────────────────────────────
def main():
    ans_keys = parse_answer_keys(download(SEITOU_URL))

    soup  = BeautifulSoup(requests.get(BASE_URL, headers=HTTP_HEADERS).text, "html.parser")
    links = [urllib.parse.urljoin(BASE_URL, a["href"])
             for a in soup.find_all("a", href=True)
             if a["href"].endswith(".pdf")]

    block_files = {}
    for url in links:
        fname = os.path.basename(urllib.parse.urlparse(url).path)
        m = re.search(r"01([a-f])_0([12])\.pdf", fname)
        if m:
            bl, ft = m.group(1).upper(), m.group(2)
            block_files.setdefault(bl, {})
            block_files[bl]["q" if ft == "1" else "img"] = download(url)

    all_qs = []
    for block in sorted(block_files.keys()):
        files   = block_files[block]
        img_map = parse_supplement_images(files["img"], block) if "img" in files else {}
        if "q" in files:
            qs = parse_questions(files["q"], block, ans_keys, img_map)
            for q in qs:
                q["explanation"] = generate_explanation(q)
            all_qs.extend(qs)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_qs, f, ensure_ascii=False, indent=2)

    total = len(all_qs)
    print(f"\n[DONE] {total} questions → {DATA_FILE}")
    from collections import Counter
    cnts = Counter(q["num"] for q in all_qs)
    block_cnts = Counter(q["category"] for q in all_qs)
    for bl, cnt in sorted(block_cnts.items()):
        print(f"  {bl}: {cnt}")


if __name__ == "__main__":
    main()
