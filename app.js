// State
let allData = [];
let currentBlockData = [];
let currentBlock = 'A';
let currentIndex = 0;
let hasAnswered = false;
let currentSelectedIndices = [];
let userAnswers = {};
let bookmarks = [];

// Multi-user Profile State
let currentUser = localStorage.getItem('med_exam_current_user') || 'デフォルト';
let userList = JSON.parse(localStorage.getItem('med_exam_user_list')) || ['デフォルト'];
if (!userList.includes(currentUser)) {
    userList.push(currentUser);
}

// DOM Elements
const views = {
    dashboard: document.getElementById('view-dashboard'),
    practice: document.getElementById('view-practice')
};

const btnHome = document.getElementById('btn-home');
const btnToggleQList = document.getElementById('btn-toggle-qlist');
const qGridContainer = document.getElementById('question-grid-container');

// LocalStorage helpers (User specific)
function loadSavedData() {
    try {
        const keyAnswers = `med_exam_user_answers_${currentUser}`;
        const keyBookmarks = `med_exam_bookmarks_${currentUser}`;

        // Backward compatibility migration for initial default user
        const oldAnswers = localStorage.getItem('med_exam_user_answers');
        const oldBookmarks = localStorage.getItem('med_exam_bookmarks');
        if (oldAnswers && !localStorage.getItem(keyAnswers) && currentUser === 'デフォルト') {
            localStorage.setItem(keyAnswers, oldAnswers);
        }
        if (oldBookmarks && !localStorage.getItem(keyBookmarks) && currentUser === 'デフォルト') {
            localStorage.setItem(keyBookmarks, oldBookmarks);
        }

        const savedAnswers = localStorage.getItem(keyAnswers);
        userAnswers = savedAnswers ? JSON.parse(savedAnswers) : {};

        const savedBookmarks = localStorage.getItem(keyBookmarks);
        bookmarks = savedBookmarks ? JSON.parse(savedBookmarks) : [];
    } catch (e) {
        console.error("Failed to load saved data from localStorage", e);
    }
}

function saveData() {
    try {
        const keyAnswers = `med_exam_user_answers_${currentUser}`;
        const keyBookmarks = `med_exam_bookmarks_${currentUser}`;
        localStorage.setItem(keyAnswers, JSON.stringify(userAnswers));
        localStorage.setItem(keyBookmarks, JSON.stringify(bookmarks));
        localStorage.setItem('med_exam_current_user', currentUser);
        localStorage.setItem('med_exam_user_list', JSON.stringify(userList));
    } catch (e) {
        console.error("Failed to save data to localStorage", e);
    }
}

// User Profile Management Functions
function renderUserUI() {
    const userDisplay = document.getElementById('current-user-display');
    if (userDisplay) userDisplay.textContent = currentUser;

    const dropdown = document.getElementById('user-select-dropdown');
    if (dropdown) {
        dropdown.innerHTML = '';
        userList.forEach(u => {
            const opt = document.createElement('option');
            opt.value = u;
            opt.textContent = u;
            if (u === currentUser) opt.selected = true;
            dropdown.appendChild(opt);
        });
    }
}

function switchUser(newUserName) {
    if (!newUserName || newUserName === currentUser) return;
    currentUser = newUserName;
    saveData();
    loadSavedData();
    renderUserUI();
    updateDashboardStats();
}

function addNewUser() {
    const name = prompt("新しい学習者（プロファイル）のお名前を入力してください:", "");
    if (!name) return;
    const cleanName = name.trim();
    if (!cleanName) return;

    if (!userList.includes(cleanName)) {
        userList.push(cleanName);
    }
    switchUser(cleanName);
}

function resetData() {
    if (confirm(`プロファイル「${currentUser}」の全ての解答記録およびブックマークを削除して初期化しますか？`)) {
        userAnswers = {};
        bookmarks = [];
        saveData();
        updateDashboardStats();
        alert(`プロファイル「${currentUser}」の学習データを初期化しました。`);
    }
}

// Export study history to JSON file
function exportData() {
    const exportObj = {
        version: 1,
        exportedAt: new Date().toISOString(),
        userAnswers: userAnswers,
        bookmarks: bookmarks
    };
    const json = JSON.stringify(exportObj, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const date = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `kokushi_history_${date}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

// Import study history from JSON file
function importData(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = JSON.parse(e.target.result);
            if (!data.userAnswers) {
                throw new Error('形式が不正です');
            }
            const importCount = Object.keys(data.userAnswers).length;
            const importBookmarks = (data.bookmarks || []).length;

            if (confirm(`ファイルの内容：\n• 解答済み ${importCount}問\n• ブックマーク ${importBookmarks}件\n\n現在の履歴に上書きして復元しますか？`)) {
                userAnswers = data.userAnswers;
                bookmarks = data.bookmarks || [];
                saveData();
                updateDashboardStats();
                alert(`復元完了！\n${importCount}問の解答履歴を読み込みました。`);
            }
        } catch (err) {
            alert('読み込み失敗：正しい形式のJSONファイルではありません。\n' + err.message);
        }
        // inputをリセット（同じファイルを再度読み込めるように）
        event.target.value = '';
    };
    reader.readAsText(file);
}

// Update Dashboard Statistics
function updateDashboardStats() {
    const total = allData.length || 395;
    const solvedKeys = Object.keys(userAnswers);
    const solvedCount = solvedKeys.length;
    
    let correctCount = 0;
    let wrongCount = 0;
    
    solvedKeys.forEach(id => {
        if (userAnswers[id].isCorrect) {
            correctCount++;
        } else {
            wrongCount++;
        }
    });
    
    const accuracyRate = solvedCount > 0 ? ((correctCount / solvedCount) * 100).toFixed(1) : "0.0";
    const overallRate = total > 0 ? ((solvedCount / total) * 100).toFixed(1) : "0.0";
    
    const statSolved = document.getElementById('stat-solved');
    if (statSolved) statSolved.textContent = `${solvedCount} / ${total}`;
    
    const statAccuracy = document.getElementById('stat-accuracy');
    if (statAccuracy) statAccuracy.textContent = `${accuracyRate}%`;
    
    const statWrong = document.getElementById('stat-wrong');
    if (statWrong) statWrong.textContent = `${wrongCount}`;
    
    const statBookmark = document.getElementById('stat-bookmark');
    if (statBookmark) statBookmark.textContent = `${bookmarks.length}`;
    
    const overallRateBadge = document.getElementById('overall-rate-badge');
    if (overallRateBadge) overallRateBadge.textContent = `${overallRate}% 達成`;
    
    const overallProgressBar = document.getElementById('overall-progress-bar');
    if (overallProgressBar) overallProgressBar.style.width = `${overallRate}%`;
    
    const weaknessText = document.getElementById('weakness-count-text');
    if (weaknessText) weaknessText.textContent = `過去に間違えた問題（${wrongCount}問）を復習`;
    
    const bookmarkText = document.getElementById('bookmark-count-text');
    if (bookmarkText) bookmarkText.textContent = `お気に入りに登録した問題（${bookmarks.length}問）`;
    
    // Update block progress labels
    ['A', 'B', 'C', 'D', 'E', 'F'].forEach(block => {
        const blockQuestions = allData.filter(q => q.id.includes(`ブロック ${block}`));
        const bTotal = blockQuestions.length;
        const bSolved = blockQuestions.filter(q => userAnswers[q.id]).length;
        const elem = document.getElementById(`block-progress-${block}`);
        if (elem) {
            elem.textContent = `(${bSolved}/${bTotal})`;
        }
    });

    // Update Specialty progress labels
    const specialties = [
        "循環器", "消化器", "公衆衛生・医療倫理", "神経・精神", 
        "呼吸器", "産婦人科", "小児科", "腎・尿路", 
        "整形・皮膚・感覚器", "血液・免疫・腫瘍", "内分泌・代謝", "救急・麻酔・総合"
    ];
    specialties.forEach(spec => {
        const specQuestions = allData.filter(q => q.specialty === spec);
        const sTotal = specQuestions.length;
        const sSolved = specQuestions.filter(q => userAnswers[q.id]).length;
        const elem = document.getElementById(`spec-stat-${spec}`);
        if (elem) {
            elem.textContent = `${sSolved} / ${sTotal}問`;
        }
    });
}

// Init
async function init() {
    try {
        const res = await fetch('data/questions.json');
        allData = await res.json();
        console.log("Total Data loaded", allData.length);
    } catch (e) {
        console.error("Failed to load data", e);
        alert("データの読み込みに失敗しました。");
    }

    loadSavedData();
    renderUserUI();
    updateDashboardStats();

    // User Profile Event Listeners
    const userDropdown = document.getElementById('user-select-dropdown');
    if (userDropdown) {
        userDropdown.addEventListener('change', (e) => switchUser(e.target.value));
    }
    const btnAddUser = document.getElementById('btn-add-user');
    if (btnAddUser) {
        btnAddUser.addEventListener('click', addNewUser);
    }

    // Event Listeners
    btnHome.addEventListener('click', showDashboard);
    btnToggleQList.addEventListener('click', toggleQuestionGrid);

    const btnSubmitAnswer = document.getElementById('btn-submit-answer');
    if (btnSubmitAnswer) {
        btnSubmitAnswer.addEventListener('click', submitAnswer);
    }

    // Special Modes & Reset Events
    const btnWeakness = document.getElementById('btn-mode-weakness');
    if (btnWeakness) btnWeakness.addEventListener('click', startWeaknessPractice);

    const btnBookmarkMode = document.getElementById('btn-mode-bookmark');
    if (btnBookmarkMode) btnBookmarkMode.addEventListener('click', startBookmarkPractice);

    const btnReset = document.getElementById('btn-reset-data');
    if (btnReset) btnReset.addEventListener('click', resetData);

    // Export / Import event listeners
    const btnExport = document.getElementById('btn-export-data');
    if (btnExport) btnExport.addEventListener('click', exportData);

    const fileImportInput = document.getElementById('file-import-input');
    if (fileImportInput) fileImportInput.addEventListener('change', importData);

    const btnBookmarkTag = document.getElementById('btn-bookmark');
    if (btnBookmarkTag) btnBookmarkTag.addEventListener('click', toggleBookmarkCurrentQuestion);

    // Block Selection Event Listeners
    document.querySelectorAll('.block-card').forEach(card => {
        card.addEventListener('click', () => {
            const block = card.dataset.block;
            startBlockPractice(block);
        });
    });

    // Medical Specialty Selection Event Listeners
    document.querySelectorAll('.specialty-card').forEach(card => {
        card.addEventListener('click', () => {
            const specialty = card.dataset.specialty;
            startSpecialtyPractice(specialty);
        });
    });

    // Image Modal Elements
    document.getElementById('modal-close').addEventListener('click', closeModal);
    document.getElementById('btn-practice-next').addEventListener('click', nextQuestion);
    document.getElementById('btn-practice-prev').addEventListener('click', prevQuestion);

    setupKeyboardShortcuts();
    registerServiceWorker();
}

// Navigation
function switchView(viewName) {
    Object.values(views).forEach(v => v.classList.add('hidden'));
    Object.values(views).forEach(v => v.classList.remove('active'));
    views[viewName].classList.remove('hidden');
    setTimeout(() => views[viewName].classList.add('active'), 10);
    
    if (viewName === 'dashboard') {
        btnHome.classList.add('hidden');
        updateDashboardStats();
    } else {
        btnHome.classList.remove('hidden');
    }
}

function showDashboard() { switchView('dashboard'); }

function toggleQuestionGrid() {
    qGridContainer.classList.toggle('hidden');
}

// --- Practice Modes ---
function startBlockPractice(block) {
    currentBlock = block;
    currentBlockData = allData.filter(q => q.id.includes(`ブロック ${block}`));
    
    if (currentBlockData.length === 0) {
        return alert(`ブロック ${block} の問題が見つかりませんでした。`);
    }

    currentIndex = 0;
    document.getElementById('block-title-display').textContent = `ブロック ${block} 演習`;
    renderQuestionGrid();
    renderQuestion();
    switchView('practice');
}

function startSpecialtyPractice(specialty) {
    currentBlock = `SPEC_${specialty}`;
    currentBlockData = allData.filter(q => q.specialty === specialty);
    
    if (currentBlockData.length === 0) {
        return alert(`「${specialty}」分野の問題が見つかりませんでした。`);
    }

    currentIndex = 0;
    document.getElementById('block-title-display').textContent = `🩺 ${specialty} 演習（${currentBlockData.length}問）`;
    renderQuestionGrid();
    renderQuestion();
    switchView('practice');
}

function startWeaknessPractice() {
    currentBlock = 'WEAKNESS';
    currentBlockData = allData.filter(q => userAnswers[q.id] && !userAnswers[q.id].isCorrect);
    
    if (currentBlockData.length === 0) {
        return alert("復習対象の誤答問題はまだありません！");
    }

    currentIndex = 0;
    document.getElementById('block-title-display').textContent = `❌ 弱点克服演習（${currentBlockData.length}問）`;
    renderQuestionGrid();
    renderQuestion();
    switchView('practice');
}

function startBookmarkPractice() {
    currentBlock = 'BOOKMARK';
    currentBlockData = allData.filter(q => bookmarks.includes(q.id));
    
    if (currentBlockData.length === 0) {
        return alert("ブックマークされた問題はまだありません！");
    }

    currentIndex = 0;
    document.getElementById('block-title-display').textContent = `⭐ ブックマーク演習（${currentBlockData.length}問）`;
    renderQuestionGrid();
    renderQuestion();
    switchView('practice');
}

function renderQuestionGrid() {
    const grid = document.getElementById('question-number-grid');
    grid.innerHTML = '';

    currentBlockData.forEach((q, idx) => {
        const btn = document.createElement('button');
        btn.className = 'q-num-btn';
        
        btn.textContent = `問${q.num || (idx + 1)}`;

        if (q.is_renmon) {
            btn.classList.add('is-renmon-btn');
            btn.title = q.group_info ? q.group_info.title : "連問";
        }

        if (userAnswers[q.id]) {
            if (userAnswers[q.id].isCorrect) {
                btn.classList.add('answered-correct');
            } else {
                btn.classList.add('answered-wrong');
            }
        }

        if (idx === currentIndex) {
            btn.classList.add('active');
        }

        btn.onclick = () => {
            jumpToQuestion(idx);
        };

        grid.appendChild(btn);
    });
}

function jumpToQuestion(index) {
    currentIndex = index;
    qGridContainer.classList.add('hidden');
    renderQuestionGrid();
    renderQuestion();
}

function renderQuestion() {
    const q = currentBlockData[currentIndex];
    if (!q) return;

    hasAnswered = !!userAnswers[q.id];
    currentSelectedIndices = [];
    
    const requiredSelectCount = q.select_count || (q.answer_indices ? q.answer_indices.length : 1);
    const correctIndices = q.answer_indices || [q.answer_index || 0];

    // Progress Bar & Counter
    const progressPercent = ((currentIndex + 1) / currentBlockData.length) * 100;
    document.getElementById('practice-progress').style.width = `${progressPercent}%`;
    document.getElementById('practice-counter').textContent = `${currentIndex + 1} / ${currentBlockData.length}`;

    // Metadata
    document.getElementById('practice-category').textContent = q.category || '未分類';
    document.getElementById('practice-source').textContent = q.id || '';
    
    if (q.is_hisshu) {
        document.getElementById('practice-hisshu').classList.remove('hidden');
    } else {
        document.getElementById('practice-hisshu').classList.add('hidden');
    }

    if (requiredSelectCount > 1) {
        const multiTag = document.getElementById('practice-multi-tag');
        multiTag.textContent = `✌️ ${requiredSelectCount}つ選択`;
        multiTag.classList.remove('hidden');
    } else {
        document.getElementById('practice-multi-tag').classList.add('hidden');
    }

    // Linked Questions (連問) Tag & Banner
    const renmonTag = document.getElementById('practice-renmon-tag');
    const renmonBanner = document.getElementById('practice-renmon-banner');
    const renmonStemText = document.getElementById('practice-renmon-stem-text');

    if (q.is_renmon && q.group_info) {
        renmonTag.textContent = `🔗 ${q.group_info.title}`;
        renmonTag.classList.remove('hidden');
        
        renmonStemText.textContent = q.group_info.stem || "共通臨床症例問題";
        renmonBanner.classList.remove('hidden');
    } else {
        renmonTag.classList.add('hidden');
        renmonBanner.classList.add('hidden');
    }

    // Bookmark Tag UI Update
    updateBookmarkButtonUI(q.id);

    // Question Text
    document.getElementById('practice-question-text').textContent = q.question;
    
    // Multiple Images Gallery
    const galleryContainer = document.getElementById('practice-images-gallery');
    galleryContainer.innerHTML = '';
    
    const imgUrls = q.image_urls || (q.image_url ? [q.image_url] : []);
    if (imgUrls.length > 0) {
        galleryContainer.classList.remove('hidden');
        imgUrls.forEach((url, idx) => {
            const card = document.createElement('div');
            card.className = 'gallery-img-card';
            
            const img = document.createElement('img');
            img.src = url;
            img.alt = `Clinical Image ${idx + 1}`;
            img.className = 'clinical-img';
            img.onclick = () => openModal(url);
            
            const hint = document.createElement('p');
            hint.className = 'img-hint';
            hint.textContent = `※画像 (${idx + 1}/${imgUrls.length}) タップで拡大`;
            
            card.appendChild(img);
            card.appendChild(hint);
            galleryContainer.appendChild(card);
        });
    } else {
        galleryContainer.classList.add('hidden');
    }

    // Multi-select Prompt Banner
    const promptBanner = document.getElementById('multi-select-prompt');
    const promptText = document.getElementById('multi-select-prompt-text');
    
    if (requiredSelectCount > 1 && !hasAnswered) {
        promptText.textContent = `💡 この問題は【${requiredSelectCount}つ】選択してください (選択中: 0/${requiredSelectCount})`;
        promptBanner.classList.remove('hidden');
    } else {
        promptBanner.classList.add('hidden');
    }

    // Options
    const optionsContainer = document.getElementById('practice-options');
    optionsContainer.innerHTML = '';
    
    q.options.forEach((opt, idx) => {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.id = `opt-btn-${idx}`;
        const optLabel = String.fromCharCode(0xff41 + idx); // ａ, ｂ, ｃ, ｄ, ｅ
        btn.innerHTML = `<span style="font-weight:bold; margin-right:8px; color:var(--primary);">${optLabel}.</span> ${opt}`;

        if (hasAnswered) {
            btn.disabled = true;
            const userAns = userAnswers[q.id];
            const isTargetCorrect = correctIndices.includes(idx);
            const isUserSelected = userAns.selectedIndices.includes(idx);
            
            if (isTargetCorrect) {
                btn.classList.add('correct');
            } else if (isUserSelected && !isTargetCorrect) {
                btn.classList.add('wrong');
            }
        } else {
            btn.onclick = () => handleOptionClick(idx, requiredSelectCount);
        }
        
        optionsContainer.appendChild(btn);
    });

    // Submit Answer Button
    const submitBtnContainer = document.getElementById('submit-btn-container');
    const submitBtn = document.getElementById('btn-submit-answer');
    if (hasAnswered) {
        submitBtnContainer.classList.add('hidden');
    } else {
        submitBtnContainer.classList.remove('hidden');
        submitBtn.disabled = true;
        if (requiredSelectCount > 1) {
            submitBtn.textContent = `解答を確定する (0/${requiredSelectCount})`;
        } else {
            submitBtn.textContent = "選択肢を選んでください";
        }
    }

    // Result Box
    const resultBox = document.getElementById('practice-result');
    if (hasAnswered) {
        const userAns = userAnswers[q.id];
        const resultTitle = document.getElementById('practice-result-title');
        
        resultBox.classList.remove('hidden');
        if (userAns.isCorrect) {
            resultTitle.textContent = "⭕ 完全正解！";
            resultTitle.style.color = "var(--success)";
        } else {
            resultTitle.textContent = "❌ 不正解...";
            resultTitle.style.color = "var(--danger)";
        }
        
        document.getElementById('practice-explanation-text').textContent = q.explanation;
        
        const mnemonicBox = document.getElementById('practice-mnemonic-container');
        const mnemonicText = document.getElementById('practice-mnemonic-text');
        if (q.mnemonic) {
            mnemonicText.textContent = q.mnemonic;
            mnemonicBox.classList.remove('hidden');
        } else {
            mnemonicBox.classList.add('hidden');
        }
    } else {
        resultBox.classList.add('hidden');
    }
}

function handleOptionClick(idx, requiredSelectCount) {
    if (hasAnswered) return;

    const btn = document.getElementById(`opt-btn-${idx}`);
    if (!btn) return;
    
    if (requiredSelectCount === 1) {
        if (currentSelectedIndices.includes(idx)) {
            currentSelectedIndices = [];
            btn.classList.remove('selected');
        } else {
            document.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
            currentSelectedIndices = [idx];
            btn.classList.add('selected');
        }
    } else {
        const selIdx = currentSelectedIndices.indexOf(idx);
        if (selIdx >= 0) {
            currentSelectedIndices.splice(selIdx, 1);
            btn.classList.remove('selected');
        } else {
            if (currentSelectedIndices.length < requiredSelectCount) {
                currentSelectedIndices.push(idx);
                btn.classList.add('selected');
            }
        }
        
        const promptText = document.getElementById('multi-select-prompt-text');
        promptText.textContent = `💡 この問題は【${requiredSelectCount}つ】選択してください (選択中: ${currentSelectedIndices.length}/${requiredSelectCount})`;
    }

    const submitBtn = document.getElementById('btn-submit-answer');
    if (requiredSelectCount === 1) {
        if (currentSelectedIndices.length === 1) {
            submitBtn.disabled = false;
            submitBtn.textContent = "解答を確定する";
        } else {
            submitBtn.disabled = true;
            submitBtn.textContent = "選択肢を選んでください";
        }
    } else {
        if (currentSelectedIndices.length === requiredSelectCount) {
            submitBtn.disabled = false;
            submitBtn.textContent = `解答を確定する (${currentSelectedIndices.length}/${requiredSelectCount})`;
        } else {
            submitBtn.disabled = true;
            submitBtn.textContent = `選択肢を選んでください (${currentSelectedIndices.length}/${requiredSelectCount})`;
        }
    }
}

function submitAnswer() {
    if (hasAnswered || currentSelectedIndices.length === 0) return;

    const q = currentBlockData[currentIndex];
    const requiredSelectCount = q.select_count || (q.answer_indices ? q.answer_indices.length : 1);
    const correctIndices = q.answer_indices || [q.answer_index || 0];

    if (currentSelectedIndices.length !== requiredSelectCount) return;

    const sortedSelected = [...currentSelectedIndices].sort();
    const sortedCorrect = [...correctIndices].sort();

    const isCorrect = sortedSelected.length === sortedCorrect.length &&
        sortedSelected.every((val, index) => val === sortedCorrect[index]);

    userAnswers[q.id] = {
        selectedIndices: [...currentSelectedIndices],
        isCorrect
    };

    saveData();
    updateDashboardStats();
    renderQuestionGrid();
    renderQuestion();
}

function toggleBookmarkCurrentQuestion() {
    const q = currentBlockData[currentIndex];
    if (!q) return;

    const bIdx = bookmarks.indexOf(q.id);
    if (bIdx >= 0) {
        bookmarks.splice(bIdx, 1);
    } else {
        bookmarks.push(q.id);
    }
    saveData();
    updateDashboardStats();
    updateBookmarkButtonUI(q.id);
}

function updateBookmarkButtonUI(qId) {
    const btn = document.getElementById('btn-bookmark');
    if (!btn) return;
    if (bookmarks.includes(qId)) {
        btn.classList.add('active');
        btn.textContent = '★ ブックマーク済み';
    } else {
        btn.classList.remove('active');
        btn.textContent = '☆ ブックマーク';
    }
}

function setupKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
        if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

        const modal = document.getElementById('image-modal');
        if (modal && !modal.classList.contains('hidden')) {
            if (e.key === 'Escape') closeModal();
            return;
        }

        const practiceView = document.getElementById('view-practice');
        if (!practiceView || practiceView.classList.contains('hidden')) return;

        if (e.key === 'Escape') {
            if (!qGridContainer.classList.contains('hidden')) {
                qGridContainer.classList.add('hidden');
            }
            return;
        }

        const q = currentBlockData[currentIndex];
        if (!q) return;

        const requiredSelectCount = q.select_count || (q.answer_indices ? q.answer_indices.length : 1);

        if (['1', '2', '3', '4', '5'].includes(e.key)) {
            const optIndex = parseInt(e.key, 10) - 1;
            if (optIndex < q.options.length && !hasAnswered) {
                handleOptionClick(optIndex, requiredSelectCount);
            }
        } else if (['a', 'b', 'c', 'd', 'e', 'A', 'B', 'C', 'D', 'E'].includes(e.key)) {
            const charCode = e.key.toLowerCase().charCodeAt(0);
            const optIndex = charCode - 97;
            if (optIndex >= 0 && optIndex < q.options.length && !hasAnswered) {
                handleOptionClick(optIndex, requiredSelectCount);
            }
        } else if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            if (!hasAnswered) {
                const submitBtn = document.getElementById('btn-submit-answer');
                if (submitBtn && !submitBtn.disabled) {
                    submitAnswer();
                }
            } else {
                nextQuestion();
            }
        } else if (e.key === 'ArrowRight') {
            nextQuestion();
        } else if (e.key === 'ArrowLeft') {
            prevQuestion();
        }
    });
}

function nextQuestion() {
    if (currentIndex < currentBlockData.length - 1) {
        currentIndex++;
        renderQuestionGrid();
        renderQuestion();
    } else {
        alert("このブロックの最後まで到達しました！");
    }
}

function prevQuestion() {
    if (currentIndex > 0) {
        currentIndex--;
        renderQuestionGrid();
        renderQuestion();
    }
}

// Modal logic
function openModal(url) {
    document.getElementById('modal-img').src = url;
    document.getElementById('image-modal').classList.remove('hidden');
}
function closeModal() {
    document.getElementById('image-modal').classList.add('hidden');
}

// PWA Service Worker Registration
function registerServiceWorker() {
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('./sw.js').then((reg) => {
                console.log('[PWA] ServiceWorker registered successfully:', reg.scope);
            }).catch((err) => {
                console.log('[PWA] ServiceWorker registration failed:', err);
            });
        });
    }
}

// Start
document.addEventListener('DOMContentLoaded', init);

