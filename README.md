# 康軒一年級國語聽寫練習

給家長操作、給小一孩子聽寫用的單頁工具。網頁播放句子 → 孩子紙上手寫、標題號 → 家長拍照上傳 → AI 判讀 → 家長確認 → 判斷需要再練的字，含有這些字的句子會留在「加強練習」清單，直到那個字被判斷寫對為止。

背景與使用方式詳見 [免費版使用與新版規劃.md](免費版使用與新版規劃.md)；完整生字/詞語/例句內容見 [康軒一年級國語複習內容.md](康軒一年級國語複習內容.md)。

## 檔案與資料流

```
vocabulary.json         原始字表（每課生字、詞語、來源連結）— 唯一的「事實來源」
        │
        ├─▶ review-data.json        73 句，逐課出題（保留學期／課次資訊）
        └─▶ optimized-review.json   39 句，全年精簡覆蓋題庫（第一輪優先使用）
                    │
                    ▼
              build_html.py  ──▶  index.html（家長／孩子實際使用的頁面）
```

- `build_html.py` 預設優先讀 `optimized-review.json`；只有這份不存在時才會退回 `review-data.json`。
- `index.html` 是產出物，**不要手動修改**；要改內容一律改 JSON 再重新產生（`python3 build_html.py`）。
- `grade_photo.py` / `local_server.py` 是判讀照片用的程式，見下方「自動判讀」。

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

改題庫的建議流程：改 JSON → 跑對應的 `validate_*.py` 確認沒破壞規則 → 跑 `build_html.py` → 實際試播放與核對一輪。

## 使用方式

兩種練習方式：

- **逐句練習**：依題庫順序，全部 39 句。
- **加強練習**：只列出「含有還沒寫對的字」的句子；一個字被 AI 判讀＋家長確認寫對後，會從清單移除，含有這個字（且沒有其他還沒寫對的字）的句子就會跟著從加強練習消失。還沒寫對的字清單在「複習記錄」分頁，可以隨時看。

練習記錄（還沒寫對的字、看過答案的句子）存在瀏覽器的 localStorage，只留在同一台裝置、同一個瀏覽器；換裝置前請先在「複習記錄」分頁匯出 JSON 備份，再到另一台匯入。

## 自動判讀（用 Codex CLI，不需要另外付費的 API）

`grade_photo.py` 和 `local_server.py` 會呼叫本機的 [OpenAI Codex CLI](https://github.com/openai/codex)（`codex exec` 非互動模式），沿用 `codex login` 登入的 ChatGPT/Codex 訂閱額度，不需要另外申請、貼上 API 金鑰。第一次使用前：

```bash
npm install -g @openai/codex
codex login   # 用 ChatGPT 帳號登入；codex login status 可確認狀態
```

### 主要方式：本機伺服器，網頁裡直接拍照上傳

```bash
python3 local_server.py
```

會印出兩個網址：`http://localhost:8787/`（這台電腦用）和 `http://<這台電腦的區網 IP>:8787/`（手機用，手機需和這台電腦連同一個 WiFi）。用這個網址開啟練習頁，跟平常一樣選句、播放；孩子寫完、標好題號後，勾選「我已確認這些題號都寫完了」，按「拍照上傳，自動判讀」，AI 判讀結果會自動出現在「複習記錄」分頁讓家長核對。開著這個終端機視窗，網頁的上傳功能才能用；關掉（Ctrl+C）之後，網頁仍可正常練習，只是拍照上傳會失效，可以改用下面的手動方式。

### 備用方式：終端機手動執行

沒開 `local_server.py`，或想在另一台電腦上跑判讀時，可以：

1. 拍照後執行：
   ```bash
   python3 grade_photo.py --photo photo.jpg
   ```
   多張照片可重複給 `--photo`。這支腳本假設用的是「逐句練習」模式（題號固定對應 `optimized-review.json` 的順序），會自動讀出照片上寫的題號，不需要另外匯出批次檔。完成後產生 `判讀結果.json`，並在終端機印出初步判斷需要再練的字。
2. 回到網頁「複習記錄」分頁「核對 AI 判讀結果」下方的「用終端機手動跑 grade_photo.py？在這裡載入結果」，載入產生的 JSON，跟自動上傳一樣需要家長勾選確認才會寫入。
3. 沒有 `codex` 或不想用本機判讀時，練習頁裡還留了「產生核對文字（給 ChatGPT）」，複製文字手動貼去 [ChatGPT](https://chatgpt.com/) 網頁核對，一樣可以人工把需要練的字勾選回網頁。

### 注意事項

- `grade_photo.py`／`local_server.py` 都只呼叫 `codex exec`（唯讀 sandbox，不會執行任何程式碼、不會修改檔案），純粹是把題目/照片送進模型換回結構化 JSON。
- 判讀品質取決於照片清晰度與模型本身，仍可能誤判；「需確認」「空白」不要直接當成「不會」，這點跟手動貼去 ChatGPT 核對的原則一致（見 [免費版使用與新版規劃.md](免費版使用與新版規劃.md)）。任何一個字沒被判讀到，程式會強制標成「需確認」，不會悄悄漏掉。
- 如果 `codex exec` 回報額度不足或未登入，先跑 `codex login status` 確認登入狀態；這兩支腳本用的是你 Codex/ChatGPT 訂閱的額度，不是另外計費的 API key。
