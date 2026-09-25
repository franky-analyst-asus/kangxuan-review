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
