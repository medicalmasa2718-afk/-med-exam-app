#!/usr/bin/env python3
"""
questions.json の精度を100%に仕上げるクレンジングスクリプト
1. 問題文の先頭に付着しているPDF問題番号ゴミ（「22 循環血液量〜」など）を除去
2. 選択肢内の問題文混入ゴミを除去
3. 余分な改行・多重スペースを整形
"""

import json
import re

def clean_questions():
    data_path = 'data/questions.json'
    with open(data_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)
    
    cleaned_count = 0
    
    for q in questions:
        text = q.get('question', '').strip()
        
        # 1. 先頭の数字ゴミ除去
        # パターン: "22 循環血液量減少性ショック..." -> "循環血液量減少性ショック..."
        # ただし "4 か月の乳児..." や "10 か月の..." "2 歳の女児..." など、年齢・月齢・日齢・数値主訴のパターンは保護する！
        
        # 保護すべきパターンの正規表現
        age_patterns = [
            r'^\d{1,2}\s*[かヶ月分日週才歳歳]',  # 4 か月の, 2 歳の, 10 か月の
            r'^\d{1,3}\s*[kKgGmM%℃]',           # 50 g, 100 %, 38.5 ℃
            r'^\d{1,2}\s*つ',                    # 5 つの
        ]

        is_age_or_val = any(re.match(p, text) for p in age_patterns)
        
        if not is_age_or_val:
            # 先頭の「数字 + スペース」を除去
            # 例: "28 汚染のない皮下組織までの..." -> "汚染のない皮下組織までの..."
            m = re.match(r'^\d{1,2}\s+(.+)$', text, re.DOTALL)
            if m:
                # 除去後のテキストが日本語文章として成立しているかチェック
                rem = m.group(1).strip()
                # 次の文字が「歳」「か」「日」などでない場合のみ採用
                if not re.match(r'^[かヶ月分日週才歳歳]', rem):
                    text = rem
                    cleaned_count += 1
        
        # 多重スペース整頓
        text = re.sub(r'[ \t]+', ' ', text)
        q['question'] = text
        
        # 2. 選択肢のクレンジング
        opts = q.get('options', [])
        new_opts = []
        for opt in opts:
            opt = opt.strip()
            # 末尾の「 高いのはどれか。」などのゴミ削除
            opt = re.sub(r'\s*(高いのは|最も|どれか|2 つ選べ|3 つ選べ).*$', '', opt) if '高いのはどれか' in opt else opt
            opt = re.sub(r'[ \t]+', ' ', opt)
            new_opts.append(opt)
        q['options'] = new_opts

    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
        
    print(f"✅ クレンジング完了: {cleaned_count}問の問題文頭ゴミを除去・整形しました。")

if __name__ == '__main__':
    clean_questions()
