# 康軒一年級國語聽寫練習

給家長操作、給小一孩子聽寫用的單頁離線工具。網頁播放句子 → 孩子紙上手寫 → 家長核對 → 標記需要再練的字。目前不呼叫任何模型 API，純靜態 HTML，可離線在瀏覽器開啟。

背景與使用方式詳見 [免費版使用與新版規劃.md](免費版使用與新版規劃.md)；完整生字/詞語/例句內容見 [康軒一年級國語複習內容.md](康軒一年級國語複習內容.md)。

## 檔案與資料流

```
vocabulary.json         原始字表（每課生字、詞語、來源連結）— 唯一的「事實來源」
        │
        ├─▶ review-data.json        73 句，逐課出題（保留學期／課次資訊）
        └─▶ optimized-review.json   39 句，全年精簡覆蓋題庫（第一輪優先使用）
                    │
                    ▼
              build_html.py  ──▶  index.html（唯一要交給家長使用的檔案）
```

- `build_html.py` 預設優先讀 `optimized-review.json`；只有這份不存在時才會退回 `review-data.json`。
- `index.html` 是產出物，**不要手動修改**；要改內容一律改 JSON 再重新產生。
- `ChatGPT錯字新句指令.txt` 是給家長複製貼去 ChatGPT 造新句用的指令範本，網頁內「產生錯字造句指令」按鈕會自動產生同類內容。

## 常用指令

重新產生 `index.html`（改了任一 JSON 之後都要跑一次）：

```bash
python3 build_html.py
```

驗證 `review-data.json` 是否與 `vocabulary.json` 一致（字表範圍、句子不重複、每課目標字有覆蓋到）：

```bash
python3 validate_data.py
```

驗證 `optimized-review.json`（字表範圍、句長上限、262 字全覆蓋、統計數字）：

```bash
python3 validate_optimized.py
```

改題庫的建議流程：改 JSON → 跑對應的 `validate_*.py` 確認沒破壞規則 → 跑 `build_html.py` → 在瀏覽器打開 `index.html` 實際試播放與核對一輪。

## 使用方式

直接用瀏覽器開啟 `index.html`（雙擊或拖進瀏覽器視窗即可，不需要伺服器）。練習記錄與標記的錯字存在瀏覽器的 localStorage，只留在同一台裝置、同一個瀏覽器；換裝置前請先用頁面內「複習記錄」分頁匯出 JSON 備份。

## 自動判讀（用 Codex CLI，不需要另外付費的 API）

`grade_photo.py`／`generate_sentences.py` 兩支腳本會呼叫本機的 [OpenAI Codex CLI](https://github.com/openai/codex)（`codex exec` 非互動模式），沿用 `codex login` 登入的 ChatGPT/Codex 訂閱額度，不需要另外申請、貼上 API 金鑰。第一次使用前：

```bash
npm install -g @openai/codex
codex login   # 用 ChatGPT 帳號登入；codex login status 可確認狀態
```

流程（每一步都還是由家長最後核對，AI 判讀只是初步建議，不會自動寫入記錄）：

1. 在網頁「聽寫練習」選好要考的句子，孩子寫完後，勾選「我已確認這些題號都寫完了」，按「匯出批次 JSON（給自動判讀腳本）」下載一份 `聽寫批次-YYYY-MM-DD.json`。
2. 把孩子的作答拍照，跟第 1 步的 JSON 放在看得到路徑的地方，執行：
   ```bash
   python3 grade_photo.py --batch 聽寫批次-2026-09-25.json --photo photo.jpg
   ```
   多張照片可重複給 `--photo`。完成後會產生一份 `...-判讀結果.json`，並在終端機印出初步判斷需要再練的字。
3. 回到網頁「複習記錄」分頁的「核對 AI 判讀結果」，載入第 2 步產生的 JSON。頁面會列出每句、每個字的判讀狀態，橘色是 AI 預選的「需練/需確認」；家長可以點擊增減勾選，按「採用勾選的字，加入加強練習」才會真正寫入記錄。
4. 想直接請 AI 幫忙造新句，可以：
   ```bash
   python3 generate_sentences.py --grading 聽寫批次-2026-09-25-判讀結果.json
   # 或指定字：python3 generate_sentences.py --weak 雨 停 兒
   # 或用匯出的複習記錄：python3 generate_sentences.py --record 康軒國語複習記錄-2026-09-25.json
   ```
   輸出是純文字草稿（`draft-new-sentences.txt`），程式已先檢查字表範圍、字數上限、是否重複；家長讀過確認合理後，貼到網頁「貼上家長審核後的新句」欄位即可（那裡還會再檢查一次）。

注意事項：

- 兩支腳本都只呼叫 `codex exec`（唯讀 sandbox，不會執行任何程式碼、不會修改檔案），純粹是把題目/照片送進模型換回結構化 JSON。
- 判讀品質取決於照片清晰度與模型本身，仍可能誤判；「需確認」「空白」不要直接當成「不會」，這點跟手動貼去 ChatGPT 核對的原則一致（見 [免費版使用與新版規劃.md](免費版使用與新版規劃.md)）。
- 如果 `codex exec` 回報額度不足或未登入，先跑 `codex login status` 確認登入狀態；這兩支腳本用的是你 Codex/ChatGPT 訂閱的額度，不是另外計費的 API key。
