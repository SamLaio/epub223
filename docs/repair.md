# 修復範圍與安全界線

[回到使用說明](../README.md)

## 套用範圍

EPUB2 轉換與 `--repair-only` 使用共用修復規則。規則依可確認的結構與資源判斷，不是每遇到驗證錯誤就刪掉內容。

| 類別 | 主要處理 | 保留與停止條件 |
| --- | --- | --- |
| OPF | 語言碼、metadata ID 衝突、manifest MIME 與資源引用、封面標記 | 不猜未知語言；封面衝突須有唯一既有指定 |
| 資源 | 核對檔頭、路徑與副檔名，回寫引用 | 不刪缺資源引用來掩蓋內容遺失；無副檔名 CSS 需明確 UTF-8 宣告與可解析規則 |
| XHTML | 已知非標準元素與屬性、破損段落、轉檔殘片 | 保留可見文字、ID、子元素與外來命名空間；程式碼範例不當作殘片 |
| 導覽 | nav／NCX 結構、可確認的相對路徑與目標錨點、空文件引用 | 重建目錄需標題唯一且順序一致；保留不同段落錨點與正文頁 |
| 平台殘留 | 已知書籤／Provider 檔與精確可辨識的來源宣傳 | 不因單一站名、廣告關鍵字或購書字樣刪正文 |
| CSS | 轉換流程中的相容性整理 | 完整 CSS 掃描與專項修復另交 epubCssFixer，最後仍需驗證 |

## 正文與宣傳清理

獨立純文字段落中完整等於 `<divclass="contentadv">` 的空廣告標記可清除；愛下電子書的完整已知宣傳文字，須連網域與信箱均精確符合才清除，並只處理緊接的完整匯出分隔線。保留引用、程式碼範例、錨點、未知網域及混入正文的變體。

獨立完整「歡迎關注公眾號『丹青拾字』」導流文案也按精確已知指紋清除；正式作者及排版署名、正文提及與其他帳號不套用。

清理只針對核准的完整頁面指紋、完整框線段落或同時具備站台識別與宣傳語的已知形式。正式署名、後記、引用、圖片、錨點與鄰近正文應保留；缺段、混入正文或未知變體不能推測刪除。個別規則及回歸案例可查 CHANGELOG 與測試，不以修訂日期編排操作手冊。

## 閱讀方向與連結

一般修復只有在正文明確全為橫排時才移除不相容的 spine RTL 宣告；直排、混合排版、文字 RTL、只有圖片或無法確認時保留。此規則與選用的 Kindle 直排模式不同。

本機連結指向實際且唯一的 body ID 時可改連到該頁，保留 body ID、正文與註腳錨點。外部 URL、查詢參數、重複 ID、不可解析 XML、xml:base 或 HTML base 不套用。不能為了消除錯誤直接刪掉不存在的段落錨點。

## 驗證與人工判斷

輸出後檢查 ZIP、CSS、EPUBCheck，再回讀正文、目錄與插圖。工具不能補回來源本來缺少的章節或圖片，也不能判斷所有廣告與正文的語意邊界。遇到不安全的修復，保留原檔並記錄具體失敗原因。

## 修復參考來源


當轉換結果無法通過 `epubCheck`，本專案會優先把可泛化的修復寫成
`epub3itizer` 內的 Python 規則，並補上回歸測試。以下工具只作為修復思路、
錯誤分類、驗證流程與測試案例設計的參考來源；不直接複製、移植或機械式改寫
第三方專案的程式碼。

- [calibre](https://github.com/kovidgoyal/calibre)：參考 Editor 的 Check book / auto-fix 思路。
- [Sigil](https://github.com/Sigil-Ebook/Sigil)：參考 Mend / Mend and Prettify / Mend On Open 思路。
- [rsking/epub-fixer](https://github.com/rsking/epub-fixer)
- [innocenat/kindle-epub-fix](https://github.com/innocenat/kindle-epub-fix)：參考 UTF-8 宣告與 body ID 目錄連結修復。
- [imanubdesigner/epub-kindle-fix](https://github.com/imanubdesigner/epub-kindle-fix)：另參考資源、MIME、XML 與連結檢查。
- [dliedke/Kindle-EPUB-Fix](https://github.com/dliedke/Kindle-EPUB-Fix)：參考本機瀏覽器診斷、結構與資源檢查及 JSON 報告設計；列為參考，不代表已整合其全部修復。
- [w3c/epubcheck](https://github.com/w3c/epubcheck)：作為轉換後的外部 EPUB 規範驗證工具；不是轉換必要依賴，也不能單獨判定 Kindle 轉換一定成功。
- [amanvirparhar/gempress](https://github.com/amanvirparhar/gempress)
- [Mimoja/MyBookLibrary](https://github.com/Mimoja/MyBookLibrary)
- [dankatri/epub-fixer](https://github.com/dankatri/epub-fixer)
- [chodzkos/epubforge](https://github.com/chodzkos/epubforge)
- [crdjm/epub-accessibility-fixer](https://github.com/crdjm/epub-accessibility-fixer)
- [OpenBookPublishers/obp-epub-fixup](https://github.com/OpenBookPublishers/obp-epub-fixup)
- [Hopkins1/TradSimpChinese](https://github.com/Hopkins1/TradSimpChinese)：參考簡繁轉換中的引號格式轉換方式。
- [madeindjs/epub-code-block-fixer](https://github.com/madeindjs/epub-code-block-fixer)：參考程式碼區塊、`pre` / `code` 與 XHTML 輸出清理。
- [veripublica/epubsana](https://github.com/veripublica/epubsana)：參考 EPUBCheck 類錯誤到安全修復 proposal 的分類方式。
- [RajaaKahel/epubfix](https://github.com/RajaaKahel/epubfix)：參考 Kobo / RMSDK 對現代 CSS 不相容時的 fallback 思路。
- [NRGunby/clean_epub](https://github.com/NRGunby/clean_epub)：參考掃描書常見頁首、頁碼與段落斷行污染清理。
- [cerasnix/epub-ruby-fix-for-apple-books](https://github.com/cerasnix/epub-ruby-fix-for-apple-books)：參考 ruby / rt / rp 在 Apple Books 顯示與選取相容性問題。
- [JoeCotellese/bookery](https://github.com/JoeCotellese/bookery)：參考 metadata-first 與非破壞式 EPUB metadata workflow。
- [chayprabs/epub-validate-repair](https://github.com/chayprabs/epub-validate-repair)：參考 manifest、spine、TOC、metadata 與批次驗證修復流程。



Kindle 版面相容性另參考 [Amazon 正體中文出版方向](https://kdp.amazon.com/en_US/help/topic/G27T64E65VM6JWKK) 與 [流式排版指引](https://kdp.amazon.com/en_US/help/topic/GPNJPYK298J8TRRV)。這些來源不是工具的執行時相依，也不表示 Send-to-Kindle 驗收保證。
