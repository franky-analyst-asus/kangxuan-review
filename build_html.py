#!/usr/bin/env python3
"""Build a single-file offline dictation page from the available question bank."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRIMARY = ROOT / "optimized-review.json"
FALLBACK = ROOT / "review-data.json"
VOCABULARY = ROOT / "vocabulary.json"
DESTINATION = ROOT / "index.html"


def main() -> None:
    source = PRIMARY if PRIMARY.exists() else FALLBACK
    data = json.loads(source.read_text(encoding="utf-8"))
    vocabulary = json.loads(VOCABULARY.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{source.name} must contain an object")
    if isinstance(data.get("sentences"), list) and "lessons" not in data:
        data["lessons"] = [{
            "semester": 0, "id": "optimized", "title": "全年精簡題庫",
            "url": "https://pedia.cloud.edu.tw/", "sentences": data["sentences"],
        }]
    if not isinstance(data.get("lessons"), list):
        raise ValueError(f"{source.name} must contain lessons or sentences")
    for lesson in data["lessons"]:
        if not isinstance(lesson, dict) or not isinstance(lesson.get("sentences"), list):
            raise ValueError("each lesson must contain a sentences array")
        lesson.setdefault("url", "https://pedia.cloud.edu.tw/")
    data["schoolYear"] = vocabulary["schoolYear"]
    data["allowedCharacters"] = list(dict.fromkeys(
        char for lesson in vocabulary["lessons"] for term in lesson["terms"]
        for char in term if "\u3400" <= char <= "\u9fff"
    ))
    data["sourceLinks"] = [
        {"label": f"{'上' if lesson['semester'] == 1 else '下'}學期第{index}課", "url": lesson["url"]}
        for semester in (1, 2)
        for index, lesson in enumerate((item for item in vocabulary["lessons"] if item["semester"] == semester), 1)
    ]
    data["questionBank"] = "全年精簡題庫" if source == PRIMARY else "全年練習題庫"
    # A script element is raw text: escape '<' so user content cannot close it.
    embedded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    embedded = embedded.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    html = TEMPLATE.replace("__REVIEW_DATA__", embedded)
    DESTINATION.write_text(html, encoding="utf-8")
    count = sum(len(lesson["sentences"]) for lesson in data["lessons"])
    print(f"Built {DESTINATION} from {source.name}: {count} sentences")


TEMPLATE = r'''<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>康軒國語聽寫練習</title>
  <style>
    :root { --ink:#173437; --muted:#5e7273; --paper:#f5f3e9; --card:#fffef8; --line:#d8e1dc; --green:#176a64; --green-dark:#10534e; --green-pale:#e5f1ed; --orange:#b65b3d; --orange-pale:#f9ede6; --focus:#a94f2e; }
    * { box-sizing:border-box; }
    html { scroll-behavior:smooth; }
    body { margin:0; color:var(--ink); background:var(--paper); font-family:system-ui,-apple-system,"PingFang TC","Microsoft JhengHei",sans-serif; line-height:1.55; }
    button,select,input { font:inherit; }
    button { cursor:pointer; }
    button:disabled { cursor:not-allowed; opacity:.48; }
    :focus-visible { outline:3px solid var(--focus); outline-offset:3px; }
    .wrap { width:min(100% - 32px, 1040px); margin-inline:auto; }
    header { background:linear-gradient(130deg,#e3efe8 0%,#f3f0df 100%); border-bottom:1px solid var(--line); }
    .mast { padding:28px 0 25px; }
    .eyebrow { margin:0 0 4px; color:var(--green); font-size:.8rem; font-weight:800; letter-spacing:.15em; }
    h1 { margin:0; font-size:clamp(1.8rem,5vw,2.65rem); letter-spacing:.03em; line-height:1.2; }
    .intro { max-width:620px; margin:10px 0 0; color:var(--muted); }
    main { padding:24px 0 60px; }
    .tabs { display:flex; gap:8px; margin-bottom:18px; }
    .tab { border:1px solid var(--line); background:var(--card); color:var(--ink); border-radius:999px; padding:9px 17px; font-weight:750; min-height:44px; }
    .tab[aria-selected="true"] { background:var(--ink); border-color:var(--ink); color:white; }
    .panel { background:var(--card); border:1px solid var(--line); border-radius:24px; box-shadow:0 8px 30px #1734370a; }
    .controls { padding:19px; display:grid; gap:15px; }
    .mode-row { display:flex; flex-wrap:wrap; gap:8px; }
    .mode { min-height:44px; padding:8px 14px; background:white; border:1px solid #bdccc5; border-radius:12px; color:var(--ink); font-weight:700; }
    .mode[aria-pressed="true"] { background:var(--green-pale); border-color:var(--green); color:var(--green-dark); }
    .scope-note { margin:0; color:var(--muted); font-size:.9rem; }
    .layout { display:grid; gap:18px; margin-top:18px; }
    .stage { padding:22px; min-height:380px; }
    .stage-head { display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px; }
    .pill { display:inline-flex; align-items:center; border-radius:999px; padding:5px 11px; color:var(--green-dark); background:var(--green-pale); font-size:.82rem; font-weight:800; }
    .counter { color:var(--muted); font-size:.9rem; font-weight:700; }
    h2 { margin:14px 0 7px; font-size:1.4rem; line-height:1.35; }
    .hint { margin:0; color:var(--muted); }
    .prompt { background:#f4f7f0; border:1px dashed #b6cbc0; border-radius:18px; margin:20px 0; padding:20px 16px; text-align:center; }
    .prompt .ear { display:block; font-size:2rem; line-height:1.1; margin-bottom:8px; }
    .prompt strong { display:block; font-size:1.1rem; }
    .prompt p { margin:4px 0 0; color:var(--muted); font-size:.92rem; }
    .actions { display:flex; flex-wrap:wrap; gap:9px; align-items:center; }
    .btn { min-height:48px; border-radius:13px; border:1px solid #bdccc5; background:white; color:var(--ink); padding:10px 16px; font-weight:800; }
    .btn.primary { background:var(--green); border-color:var(--green); color:white; }
    .btn.primary:hover { background:var(--green-dark); }
    .btn.soft { background:var(--green-pale); border-color:var(--green-pale); color:var(--green-dark); }
    .rate { display:flex; flex-wrap:wrap; gap:9px; align-items:center; margin:18px 0; color:var(--muted); font-size:.9rem; font-weight:700; }
    .rate input { accent-color:var(--green); width:min(220px,55vw); min-height:32px; }
    .answer { margin-top:22px; border-top:1px solid var(--line); padding-top:20px; }
    .answer-text { margin:9px 0 16px; font-size:clamp(1.55rem,6vw,2.2rem); font-weight:750; line-height:1.8; letter-spacing:.06em; overflow-wrap:anywhere; }
    .small-label { margin:0 0 8px; color:var(--muted); font-size:.84rem; font-weight:800; }
    .chip-list { display:flex; flex-wrap:wrap; gap:8px; }
    .chip { min-width:48px; min-height:48px; border:1px solid #b5cbc4; border-radius:12px; background:white; color:var(--ink); font-size:1.18rem; font-weight:800; }
    .chip[aria-pressed="true"] { color:var(--orange); border-color:#dbad97; background:var(--orange-pale); }
    .answer-foot { margin:13px 0 0; font-size:.88rem; color:var(--muted); }
    .parent-help { margin-top:24px; border-top:1px solid var(--line); padding-top:20px; }
    .parent-help h3 { margin:0 0 6px; font-size:1.05rem; }
    .parent-help .confirm { display:flex; align-items:flex-start; gap:9px; margin:14px 0; font-weight:700; }
    .parent-help .confirm input { width:20px; height:20px; accent-color:var(--green); flex:none; margin-top:2px; }
    .parent-help textarea { display:block; width:100%; min-height:190px; margin:12px 0; padding:12px; border:1px solid #bdccc5; border-radius:12px; color:var(--ink); background:white; resize:vertical; }
    a { color:var(--green-dark); text-underline-offset:3px; }
    .list { padding:19px; }
    .list h2 { margin:0 0 2px; font-size:1.1rem; }
    .item-list { list-style:none; padding:0; margin:13px 0 0; display:grid; gap:7px; max-height:480px; overflow:auto; }
    .item-list button { width:100%; min-height:50px; display:flex; align-items:center; justify-content:space-between; gap:8px; border:1px solid var(--line); border-radius:12px; background:white; color:var(--ink); padding:9px 11px; text-align:left; }
    .item-list button[aria-current="true"] { border-color:var(--green); background:var(--green-pale); }
    .item-list small { color:var(--muted); }
    .empty { border:1px dashed var(--line); border-radius:14px; padding:20px; color:var(--muted); }
    .records { padding:22px; }
    .records h2 { margin:0 0 8px; }
    .ai-sentence { border:1px solid var(--line); border-radius:14px; padding:14px; margin:12px 0; background:#f4f7f0; }
    .ai-sentence p { margin:0 0 9px; font-weight:750; }
    .ai-sentence .chip.blank { color:var(--muted); border-style:dashed; }
    .file-label[aria-disabled="true"] { opacity:.48; cursor:not-allowed; pointer-events:none; }
    .parent-help details > summary { cursor:pointer; color:var(--green-dark); font-weight:700; font-size:.92rem; }
    .stats { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin:17px 0; }
    .stat { background:#f4f7f0; border-radius:15px; padding:14px; }
    .stat strong { display:block; font-size:1.6rem; line-height:1.2; }
    .stat span { color:var(--muted); font-size:.86rem; }
    .record-actions { display:flex; flex-wrap:wrap; gap:9px; margin-top:23px; }
    .record-actions input { position:absolute; width:1px; height:1px; opacity:0; }
    .file-label { display:inline-flex; align-items:center; }
    .notice { margin-top:14px; color:var(--muted); font-size:.85rem; }
    .feedback { min-height:1.5em; color:var(--orange); font-weight:700; }
    footer { padding:26px 0 45px; color:var(--muted); font-size:.84rem; }
    [hidden] { display:none !important; }
    @media (min-width:760px) { .mast { padding:36px 0; } .layout { grid-template-columns:minmax(0,1.5fr) minmax(260px,.8fr); align-items:start; } .stage { padding:28px; } .controls { padding:22px; } }
    @media (max-width:480px) { .wrap { width:min(100% - 24px,1040px); } .stage,.records { padding:18px; } .actions .btn { flex:1 1 auto; } }
    @media (prefers-reduced-motion:reduce) { html { scroll-behavior:auto; } }
  </style>
</head>
<body>
  <header><div class="wrap mast"><p class="eyebrow">114 學年度 · 一年級國語</p><h1>康軒國語聽寫練習</h1><p class="intro">按播放，先在紙上寫下聽到的句子，再和家長核對答案。</p></div></header>
  <main class="wrap">
    <nav class="tabs" aria-label="頁面"><button type="button" id="practiceTab" class="tab" aria-selected="true">聽寫練習</button><button type="button" id="recordsTab" class="tab" aria-selected="false">複習記錄</button></nav>
    <section id="practiceView" aria-label="聽寫練習">
      <div class="panel controls">
        <div><p class="small-label">練習方式</p><div class="mode-row" role="group" aria-label="練習方式"><button type="button" class="mode" data-mode="list" aria-pressed="true">逐句練習</button><button type="button" class="mode" data-mode="review" aria-pressed="false">加強練習</button></div></div>
        <p id="scopeNote" class="scope-note"></p>
      </div>
      <div class="layout">
        <section class="panel stage" aria-label="目前聽寫">
          <div class="stage-head"><span id="lessonBadge" class="pill">請選擇句子</span><span id="counter" class="counter"></span></div>
          <h2 id="stageTitle">準備好了嗎？</h2><p id="stageHint" class="hint">從右側的清單選一句，或開始隨機練習。</p>
          <div id="activeContent" hidden>
            <div class="prompt"><span class="ear" aria-hidden="true">♫</span><strong>仔細聽，寫在紙上</strong><p>可以重聽。寫好以後再顯示答案。</p></div>
            <div class="actions"><button id="playBtn" type="button" class="btn primary">▶ 播放句子</button><button id="stopBtn" type="button" class="btn">■ 停止</button></div>
            <label class="rate">播放速度 <input id="rate" type="range" min="0.6" max="1.1" step="0.1" value="0.8"><output id="rateValue" for="rate">0.8 倍</output></label>
            <button id="revealBtn" type="button" class="btn soft">我已寫在紙上，顯示答案</button>
            <div id="answer" class="answer" hidden><p class="small-label">核對答案</p><p id="answerText" class="answer-text"></p><p class="small-label">句中想再練習的字（點選標記）</p><div id="targetChips" class="chip-list"></div><p class="answer-foot">橘色表示已加入加強練習。<a id="sourceLink" href="#" target="_blank" rel="noopener noreferrer">查看字表來源</a></p></div>
            <div class="actions" style="margin-top:20px"><button id="nextBtn" type="button" class="btn">下一句 →</button></div>
            <section class="parent-help" aria-label="家長協助核對"><h3>給家長：核對孩子的作答</h3><p class="hint">先讓孩子在紙上寫完、標好題號，再拍照上傳，AI 會自動判讀；判讀結果一律由家長確認，回到這裡標記需練的字。</p><p id="helperScope" class="scope-note"></p><label class="confirm"><input id="writtenConfirm" type="checkbox">我已確認這些題號都寫完了</label><div class="actions"><label for="gradePhotoInput" class="btn primary file-label" tabindex="0" aria-disabled="true">拍照上傳，自動判讀</label><input id="gradePhotoInput" type="file" accept="image/*" capture="environment" multiple disabled></div><p id="gradePhotoMessage" class="feedback" role="status" aria-live="polite"></p><details><summary>沒開本機伺服器？用手動方式貼去 ChatGPT</summary><button id="makePromptBtn" type="button" class="btn" disabled style="margin-top:12px">產生核對文字（給 ChatGPT）</button><div id="promptBox" hidden><textarea id="promptText" readonly aria-label="給 ChatGPT 的核對文字"></textarea><button id="copyPromptBtn" type="button" class="btn soft">複製核對文字</button><p class="notice">複製後，請自行開啟 <a href="https://chatgpt.com/" target="_blank" rel="noopener noreferrer">ChatGPT</a>，貼上文字並上傳照片。這個頁面不會傳送照片。</p><p id="copyMessage" class="feedback" role="status" aria-live="polite"></p></div></details></section>
          </div>
          <p id="speechMessage" class="feedback" role="status" aria-live="polite"></p>
        </section>
        <aside class="panel list"><h2 id="listTitle">句子清單</h2><p class="hint" id="listHint">選擇一句開始聽寫</p><ol id="sentenceList" class="item-list"></ol><div id="emptyList" class="empty" hidden></div></aside>
      </div>
    </section>
    <section id="recordsView" class="panel records" hidden aria-label="複習記錄">
      <h2>複習記錄</h2><p class="hint">記錄只存在這個瀏覽器。換裝置時，請先匯出，再在另一台匯入。</p>
      <div class="stats"><div class="stat"><strong id="reviewedCount">0</strong><span>看過答案的句子</span></div><div class="stat"><strong id="weakCount">0</strong><span>還沒寫對的字</span></div></div>
      <p class="small-label">還沒寫對的字</p><div id="weakList" class="chip-list"></div><p id="weakEmpty" class="hint">目前沒有還沒寫對的字。核對答案或拍照判讀後，這裡會列出需要再練的字。</p>
      <div class="record-actions"><button id="exportBtn" type="button" class="btn">匯出記錄 JSON</button><label for="importFile" class="btn file-label" tabindex="0">匯入記錄 JSON</label><input id="importFile" type="file" accept=".json,application/json"></div>
      <p class="notice">匯入會取代這個瀏覽器目前的複習記錄。這個工具不會同步到其他裝置，也不會自動判斷手寫對錯。</p><p id="recordMessage" class="feedback" role="status" aria-live="polite"></p>
      <section class="parent-help" aria-label="AI 判讀結果核對"><h3>核對 AI 判讀結果</h3><p class="hint">在「聽寫練習」拍照上傳後，判讀結果會自動出現在這裡。橘色是 AI 建議還沒寫對的字，白色是判斷寫對的字；點一下可以增減勾選。確認套用後：勾選的字會列入（或留在）「還沒寫對的字」，取消勾選等於確認寫對、會從清單移除——含有這個字的句子也會跟著從「加強練習」消失。AI 判斷一律先預覽，不會自動寫入。</p><p id="aiSuggestionMessage" class="feedback" role="status" aria-live="polite"></p><div id="aiSuggestionReview" hidden><div id="aiSuggestionSentences"></div><button id="applyAiSuggestionBtn" type="button" class="btn primary">確認，更新「還沒寫對的字」</button></div><details style="margin-top:14px"><summary>用終端機手動跑 grade_photo.py？在這裡載入結果</summary><div class="record-actions" style="margin-top:12px"><label for="aiSuggestionFile" class="btn file-label" tabindex="0">載入判讀結果 JSON</label><input id="aiSuggestionFile" type="file" accept=".json,application/json"></div></details></section>
    </section>
  </main>
  <footer class="wrap">本頁可直接以桌面瀏覽器開啟，離線練習。語音使用瀏覽器與作業系統提供的中文朗讀；聲音品質與可用性依裝置而異。<details><summary>查看教育百科字表來源</summary><div id="sourceLinks" class="chip-list"></div></details></footer>
  <script id="app-data" type="application/json">__REVIEW_DATA__</script>
  <script>
  (() => {
    'use strict';
    const data = JSON.parse(document.getElementById('app-data').textContent);
    const lessons = data.lessons;
    const allSentences = lessons.flatMap(lesson => lesson.sentences.map(sentence => ({...sentence, lesson})));
    const byId = new Map(allSentences.map(sentence => [sentence.id, sentence]));
    const allowedChars = new Set(data.allowedCharacters);
    const sentenceCharacters = item => [...new Set([...item.text].filter(char => allowedChars.has(char)))];
    const storageKey = 'kangxuan-dictation-114-v1';
    const $ = id => document.getElementById(id);
    const state = { mode:'list', queue:[], index:-1, revealed:false, record:loadRecord(), aiSuggestion:null };

    function freshRecord() { return { schemaVersion:1, schoolYear:data.schoolYear, weakCharacters:[], reviewed:{} }; }
    function validRecord(value, allowStaleIds = false) {
      if (!value || typeof value !== 'object' || Array.isArray(value) || value.schemaVersion !== 1 || value.schoolYear !== data.schoolYear) throw new Error('記錄版本或學年度不符合。');
      if (!Array.isArray(value.weakCharacters) || !value.reviewed || typeof value.reviewed !== 'object' || Array.isArray(value.reviewed)) throw new Error('記錄格式不正確。');
      if (value.weakCharacters.length > allowedChars.size || value.weakCharacters.some(char => typeof char !== 'string' || !allowedChars.has(char))) throw new Error('記錄含有不屬於本教材的字。');
      const weakCharacters = [...new Set(value.weakCharacters)];
      const reviewed = {};
      for (const [id, info] of Object.entries(value.reviewed)) {
        if (!byId.has(id) && allowStaleIds) continue;
        if (!byId.has(id) || !info || typeof info !== 'object' || !Number.isSafeInteger(info.count) || info.count < 1 || info.count > 1000000 || typeof info.lastViewed !== 'string' || !Number.isFinite(Date.parse(info.lastViewed))) throw new Error('句子記錄格式不正確。');
        reviewed[id] = { count:info.count, lastViewed:info.lastViewed };
      }
      return { schemaVersion:1, schoolYear:data.schoolYear, weakCharacters, reviewed };
    }
    function loadRecord() { try { const raw = localStorage.getItem(storageKey); return raw ? validRecord(JSON.parse(raw), true) : freshRecord(); } catch { return freshRecord(); } }
    function saveRecord() { try { localStorage.setItem(storageKey, JSON.stringify(state.record)); return true; } catch { $('recordMessage').textContent = '瀏覽器無法儲存記錄，請檢查儲存空間設定。'; return false; } }
    function speakStop() { if ('speechSynthesis' in window) window.speechSynthesis.cancel(); }
    function speak() {
      const item = state.queue[state.index]; if (!item) return;
      if (!('speechSynthesis' in window)) { $('speechMessage').textContent = '此瀏覽器不支援語音朗讀。'; return; }
      speakStop(); $('speechMessage').textContent = '';
      const utterance = new SpeechSynthesisUtterance(item.text);
      utterance.lang = 'zh-TW'; utterance.rate = Number($('rate').value);
      const voices = window.speechSynthesis.getVoices();
      utterance.voice = voices.find(voice => voice.lang.toLowerCase() === 'zh-tw') || voices.find(voice => voice.lang.toLowerCase().startsWith('zh')) || null;
      utterance.onerror = event => { if (event.error !== 'interrupted' && event.error !== 'canceled') $('speechMessage').textContent = '播放失敗。請檢查裝置的中文語音設定。'; };
      window.speechSynthesis.speak(utterance);
    }
    function selectView(view) {
      const practice = view === 'practice';
      $('practiceView').hidden = !practice; $('recordsView').hidden = practice;
      $('practiceTab').setAttribute('aria-selected', String(practice)); $('recordsTab').setAttribute('aria-selected', String(!practice));
      speakStop();
      if (practice) { state.revealed = false; resetHelper(); renderStage(); } else { renderRecords(); }
    }
    function candidates() {
      if (state.mode === 'review') {
        const weak = new Set(state.record.weakCharacters);
        return allSentences.filter(item => sentenceCharacters(item).some(char => weak.has(char)));
      }
      return allSentences;
    }
    function resetQueue() {
      speakStop(); state.revealed = false; state.index = -1; resetHelper();
      state.queue = candidates();
      $('scopeNote').textContent = state.mode === 'review'
        ? `${state.queue.length} 句含有還沒寫對的字，練到都寫對就會從這裡消失。`
        : `${data.questionBank}共有 ${state.queue.length} 句。`;
      renderList(); renderStage();
    }
    function selectSentence(index) { if (index < 0 || index >= state.queue.length) return; speakStop(); state.index = index; state.revealed = false; $('speechMessage').textContent = ''; resetHelper(); renderList(); renderStage(); }
    function renderList() {
      $('listTitle').textContent = state.mode === 'review' ? '加強練習句子' : '句子清單';
      $('listHint').textContent = '選擇一句開始聽寫';
      const list = $('sentenceList'); list.replaceChildren();
      $('emptyList').hidden = state.queue.length > 0;
      $('emptyList').textContent = state.mode === 'review' ? '太好了，目前沒有還沒寫對的字！' : '目前沒有句子。';
      state.queue.forEach((item,i) => {
        const li = document.createElement('li'); const button = document.createElement('button');
        button.type = 'button'; button.setAttribute('aria-current', String(i === state.index));
        const title = document.createElement('span'); title.textContent = `第 ${i+1} 句`;
        const meta = document.createElement('small'); meta.textContent = state.record.reviewed[item.id] ? '可再練習' : '開始聽寫';
        button.append(title,meta); button.addEventListener('click', () => selectSentence(i)); li.append(button); list.append(li);
      });
    }
    function renderStage() {
      const item = state.queue[state.index], active = !!item;
      $('activeContent').hidden = !active; $('answer').hidden = !active || !state.revealed;
      $('revealBtn').hidden = !active || state.revealed;
      $('lessonBadge').textContent = active ? data.questionBank : '尚未選句';
      $('counter').textContent = active ? `${state.index+1} / ${state.queue.length}` : '';
      $('stageTitle').textContent = active ? `第 ${state.index+1} 句，準備聽寫` : state.queue.length ? '準備好了嗎？' : '目前沒有可練習的句子';
      $('stageHint').textContent = active ? '先聽，再寫。需要時可重播。' : state.queue.length ? '從句子清單選一句開始。' : '請先在核對答案後標記想再練的字。';
      if (!active) return;
      renderHelperScope();
      $('nextBtn').disabled = state.index >= state.queue.length-1;
      if (state.revealed) {
        $('answerText').textContent = item.text;
        $('sourceLink').href = item.lesson.url;
        const chips = $('targetChips'); chips.replaceChildren();
        sentenceCharacters(item).forEach(char => {
          const button = document.createElement('button'); button.type = 'button'; button.className = 'chip'; button.textContent = char;
          button.setAttribute('aria-label', `${char}：${state.record.weakCharacters.includes(char) ? '取消加強' : '加入加強'}`);
          button.setAttribute('aria-pressed', String(state.record.weakCharacters.includes(char)));
          button.addEventListener('click', () => toggleWeak(char)); chips.append(button);
        });
      } else { $('answerText').textContent = ''; $('targetChips').replaceChildren(); }
    }
    function helperItems() {
      if (state.index < 0) return [];
      return state.queue.slice(state.index,state.index+5);
    }
    function renderHelperScope() {
      const items = helperItems();
      const start = state.index+1;
      $('helperScope').textContent = items.length ? `本次核對：第 ${start}～${start+items.length-1} 句，共 ${items.length} 句。` : '';
    }
    function setGradePhotoEnabled(enabled) {
      $('gradePhotoInput').disabled = !enabled;
      document.querySelector('label[for="gradePhotoInput"]').setAttribute('aria-disabled', String(!enabled));
    }
    function resetHelper() {
      $('writtenConfirm').checked = false; $('makePromptBtn').disabled = true; setGradePhotoEnabled(false);
      $('promptBox').hidden = true; $('promptText').value = ''; $('copyMessage').textContent = ''; $('gradePhotoMessage').textContent = '';
    }
    function fileToDataUrl(file) {
      return new Promise((resolve,reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error('讀取照片失敗。'));
        reader.readAsDataURL(file);
      });
    }
    async function uploadPhotosForGrading(fileList) {
      const items = helperItems();
      const files = [...(fileList || [])];
      if (!items.length || !files.length) return;
      setGradePhotoEnabled(false);
      $('gradePhotoMessage').textContent = '判讀中，請稍候（可能需要一點時間）…';
      try {
        const photos = await Promise.all(files.map(fileToDataUrl));
        const response = await fetch('/api/grade', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sentences: items.map((item,i) => ({ index:i+1, id:item.id, text:item.text })), photos }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.error || `伺服器錯誤（${response.status}）`);
        state.aiSuggestion = parseAiSuggestion({ schemaVersion:1, sentences:data.sentences || [] });
        if (!state.aiSuggestion.sentences.length) {
          $('gradePhotoMessage').textContent = '沒有在照片裡辨認出看得懂的題號或文字，請確認題號有寫清楚、照片夠亮夠近，再試一次。';
          return;
        }
        selectView('records');
        renderAiSuggestion();
        $('aiSuggestionReview').hidden = false;
        $('aiSuggestionMessage').textContent = `已判讀 ${state.aiSuggestion.sentences.length} 句。橘色的字已預選為還沒寫對，請確認後再套用；點一下可以增減勾選。`;
      } catch (error) {
        $('gradePhotoMessage').textContent = `自動判讀失敗：${error.message}。請確認 local_server.py 有在這台電腦上執行，或改用「產生核對文字」手動流程。`;
      } finally {
        setGradePhotoEnabled($('writtenConfirm').checked);
        $('gradePhotoInput').value = '';
      }
    }
    function makePrompt() {
      if (!$('writtenConfirm').checked) return;
      const items = helperItems(); if (!items.length) return;
      const start = state.index+1;
      const lines = items.map((item,i) => `第 ${start+i} 句：${item.text}`);
      $('promptText').value = [
        '請協助家長核對一年級國語聽寫照片。只根據照片上實際可見的筆跡逐字判讀；不要依正確答案推測、補字或改字。未寫的字標「空白」；看不清楚的字標「需家長確認」，不要猜。不要判斷筆順。',
        '請逐題列出「疑似寫對」「需練」「需確認」，最後列出需練的字（去除重複）。這只是輔助判讀，最後由家長確認。',
        '題目與正確句子：',
        ...lines
      ].join('\n\n');
      $('promptBox').hidden = false;
    }
    async function copyPrompt() {
      try {
        if (!navigator.clipboard || !navigator.clipboard.writeText) throw new Error('unavailable');
        await navigator.clipboard.writeText($('promptText').value);
        $('copyMessage').textContent = '已複製。請自行貼到 ChatGPT，並手動上傳照片。';
      } catch {
        $('promptText').focus(); $('promptText').select();
        $('copyMessage').textContent = '瀏覽器無法自動複製。文字已選取，請手動複製。';
      }
    }
    function toggleWeak(char) {
      const weak = new Set(state.record.weakCharacters); weak.has(char) ? weak.delete(char) : weak.add(char);
      state.record.weakCharacters = [...weak].sort((a,b) => a.localeCompare(b,'zh-Hant'));
      saveRecord(); renderStage();
    }
    function reveal() {
      const item = state.queue[state.index]; if (!item || state.revealed) return;
      speakStop(); state.revealed = true;
      const current = state.record.reviewed[item.id] || {count:0};
      state.record.reviewed[item.id] = {count:current.count+1,lastViewed:new Date().toISOString()};
      saveRecord(); renderStage();
    }
    function renderRecords() {
      $('reviewedCount').textContent = Object.keys(state.record.reviewed).length;
      $('weakCount').textContent = state.record.weakCharacters.length;
      $('weakEmpty').hidden = state.record.weakCharacters.length > 0;
      const list = $('weakList'); list.replaceChildren();
      state.record.weakCharacters.forEach(char => {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'chip';
        button.textContent = char + ' ×'; button.setAttribute('aria-label', `已經會「${char}」，取消加強`);
        button.addEventListener('click', () => { toggleWeak(char); renderRecords(); }); list.append(button);
      });
    }
    function sentenceTextById(id) {
      const known = byId.get(id);
      return known ? known.text : null;
    }
    function parseAiSuggestion(raw) {
      if (!raw || typeof raw !== 'object' || Array.isArray(raw) || raw.schemaVersion !== 1 || !Array.isArray(raw.sentences)) throw new Error('判讀結果格式不正確，請確認是 grade_photo.py 或自動判讀產生的檔案。');
      const validStatus = new Set(['correct','needs_practice','unclear','blank']);
      const sentences = raw.sentences.map((entry,i) => {
        if (!entry || typeof entry !== 'object' || typeof entry.id !== 'string') throw new Error(`第 ${i+1} 句：格式不正確。`);
        const text = sentenceTextById(entry.id);
        if (!text) throw new Error(`第 ${i+1} 句：找不到題號「${entry.id}」，題庫可能已經更新，請重新判讀。`);
        const validChars = new Set(sentenceCharacters({text}));
        if (!Array.isArray(entry.characters)) throw new Error(`第 ${i+1} 句：缺少判讀結果。`);
        const seen = new Set(); const characters = [];
        entry.characters.forEach(item => {
          if (!item || typeof item.char !== 'string' || !validStatus.has(item.status)) return;
          if (!validChars.has(item.char) || seen.has(item.char)) return;
          seen.add(item.char); characters.push({ char:item.char, status:item.status });
        });
        if (!characters.length) throw new Error(`第 ${i+1} 句：判讀結果裡沒有屬於這句的字，已忽略。`);
        return { id:entry.id, text, characters, selected:new Set(characters.filter(item => item.status !== 'correct').map(item => item.char)) };
      });
      return { generatedAt: typeof raw.generatedAt === 'string' ? raw.generatedAt : '', sentences };
    }
    function renderAiSuggestion() {
      const container = $('aiSuggestionSentences'); container.replaceChildren();
      state.aiSuggestion.sentences.forEach(sentence => {
        const box = document.createElement('div'); box.className = 'ai-sentence';
        const p = document.createElement('p'); p.textContent = sentence.text; box.append(p);
        const chips = document.createElement('div'); chips.className = 'chip-list';
        sentence.characters.forEach(item => {
          const button = document.createElement('button'); button.type = 'button';
          button.className = 'chip' + (item.status === 'blank' ? ' blank' : '');
          button.textContent = item.status === 'blank' ? `${item.char}（空白）` : item.status === 'unclear' ? `${item.char}（需確認）` : item.char;
          const active = sentence.selected.has(item.char);
          button.setAttribute('aria-pressed', String(active));
          button.setAttribute('aria-label', `${item.char}：${active ? '取消加強' : '加入加強'}`);
          button.addEventListener('click', () => { active ? sentence.selected.delete(item.char) : sentence.selected.add(item.char); renderAiSuggestion(); });
          chips.append(button);
        });
        box.append(chips); container.append(box);
      });
    }
    async function loadAiSuggestion(file) {
      if (!file) return;
      try {
        if (file.size > 2000000) throw new Error('檔案太大。');
        state.aiSuggestion = parseAiSuggestion(JSON.parse(await file.text()));
        if (!state.aiSuggestion.sentences.length) {
          $('aiSuggestionReview').hidden = true; $('aiSuggestionSentences').replaceChildren();
          $('aiSuggestionMessage').textContent = '這份判讀結果是空的，沒有辨認出任何題目，請確認照片內容後重新判讀。';
          $('aiSuggestionFile').value = '';
          return;
        }
        renderAiSuggestion();
        $('aiSuggestionReview').hidden = false;
        $('aiSuggestionMessage').textContent = `已載入 ${state.aiSuggestion.sentences.length} 句判讀結果。橘色的字已預選為還沒寫對，請確認後再套用；點一下可以增減勾選。`;
      } catch (error) {
        state.aiSuggestion = null; $('aiSuggestionReview').hidden = true; $('aiSuggestionSentences').replaceChildren();
        $('aiSuggestionMessage').textContent = `無法載入：${error.message}`;
      }
      $('aiSuggestionFile').value = '';
    }
    function applyAiSuggestion() {
      if (!state.aiSuggestion) return;
      const weak = new Set(state.record.weakCharacters);
      let added = 0, graduated = 0;
      state.aiSuggestion.sentences.forEach(sentence => {
        sentence.characters.forEach(item => {
          const keep = sentence.selected.has(item.char);
          if (keep && !weak.has(item.char)) { weak.add(item.char); added++; }
          else if (!keep && weak.has(item.char)) { weak.delete(item.char); graduated++; }
        });
      });
      state.record.weakCharacters = [...weak].sort((a,b) => a.localeCompare(b,'zh-Hant'));
      saveRecord();
      const parts = [];
      if (added) parts.push(`加入 ${added} 個還沒寫對的字`);
      if (graduated) parts.push(`確認 ${graduated} 個字寫對了，已從清單移除`);
      $('aiSuggestionMessage').textContent = parts.length ? `已確認：${parts.join('、')}。` : '已確認，清單沒有變動。';
      $('aiSuggestionReview').hidden = true; $('aiSuggestionSentences').replaceChildren();
      state.aiSuggestion = null;
      renderRecords();
      if (state.mode === 'review') resetQueue();
    }
    function exportRecord() {
      const blob = new Blob([JSON.stringify(state.record,null,2)],{type:'application/json'});
      const url = URL.createObjectURL(blob); const link = document.createElement('a');
      link.href = url; link.download = `康軒國語複習記錄-${new Date().toISOString().slice(0,10)}.json`;
      document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url),1000);
      $('recordMessage').textContent = '已匯出記錄。';
    }
    async function importRecord(file) {
      if (!file) return;
      try {
        if (file.size > 1000000) throw new Error('檔案太大。');
        const parsed = JSON.parse(await file.text());
        state.record = validRecord(parsed); saveRecord(); renderRecords();
        $('recordMessage').textContent = '匯入完成，已取代本裝置的記錄。';
        if (state.mode === 'review') resetQueue();
      } catch (error) { $('recordMessage').textContent = `無法匯入：${error.message}`; }
      $('importFile').value = '';
    }
    $('practiceTab').addEventListener('click', () => selectView('practice'));
    $('recordsTab').addEventListener('click', () => selectView('records'));
    document.querySelectorAll('.mode').forEach(button => button.addEventListener('click', () => { state.mode = button.dataset.mode; document.querySelectorAll('.mode').forEach(item => item.setAttribute('aria-pressed', String(item === button))); resetQueue(); }));
    $('playBtn').addEventListener('click', speak); $('stopBtn').addEventListener('click', speakStop);
    $('revealBtn').addEventListener('click', reveal); $('nextBtn').addEventListener('click', () => selectSentence(state.index+1));
    $('writtenConfirm').addEventListener('change', event => { $('makePromptBtn').disabled = !event.target.checked; setGradePhotoEnabled(event.target.checked); if (!event.target.checked) { $('promptBox').hidden = true; $('promptText').value = ''; } });
    $('makePromptBtn').addEventListener('click', makePrompt); $('copyPromptBtn').addEventListener('click', copyPrompt);
    $('gradePhotoInput').addEventListener('change', event => uploadPhotosForGrading(event.target.files));
    $('aiSuggestionFile').addEventListener('change', event => loadAiSuggestion(event.target.files[0]));
    $('applyAiSuggestionBtn').addEventListener('click', applyAiSuggestion);
    $('rate').addEventListener('input', event => { $('rateValue').textContent = `${Number(event.target.value).toFixed(1)} 倍`; });
    $('exportBtn').addEventListener('click', exportRecord);
    $('importFile').addEventListener('change', event => importRecord(event.target.files[0]));
    document.querySelectorAll('.file-label').forEach(label => label.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); $(label.getAttribute('for')).click(); } }));
    data.sourceLinks.forEach(link => { const a = document.createElement('a'); a.href = link.url; a.target = '_blank'; a.rel = 'noopener noreferrer'; a.textContent = link.label; $('sourceLinks').append(a); });
    resetQueue();
  })();
  </script>
</body>
</html>
'''

if __name__ == "__main__":
    main()
