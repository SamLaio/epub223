# ePub223 1.9

## 1.9 更新

- 修正同步朗讀SMIL類型及時長、保留合法OPF scheme與media refinement，保護固定版面與日文原文。
- 保留不同目錄目標，僅在完整唯一標題證據成立時重建全失聯目錄；保留cc卷名樣式。
- 以精確指紋與安全邊界清理已核實來源宣傳；辨識無副檔名的明確UTF-8 CSS，避免Sigil未知媒體類型警告。

來源宣傳清理僅接受核實的完整錄入組頁面文字指紋，或完整鏡文學導流句＋已核准純 QR 圖；若仍有連結，必須指向官網，亦支援上游將該連結轉成 span 的結果。保留相鄰番外／試閱正文、未知圖片與共用資源；刪頁後同步修正書目及導覽引用。

OPF 書目清理保留 EPUB3 `meta` 的合法 `scheme`（例如 `role` 的 `marc:relators`）；修正非法屬性時不會一併刪除角色詞彙定義。

同步朗讀會保留原有 `media:*` 書目、指向 manifest 的合法時長 refinement 與 SMIL／音訊。依包內實際 SMIL 補正 `application/smil+xml`，並僅在缺值時由明確 `clipBegin`／`clipEnd` 補上逐檔時長；全書時長補齊或調整為逐檔總和。缺少結束點或無法解析的時間會停止，不猜測。參照 [W3C Media Overlays](https://www.w3.org/publishing/epub32/epub-mediaoverlays.html)，沿用 Calibre Check book／Sigil 保留內容、修復後重新驗證的原則，未移植第三方程式碼。

固定版面 viewport 補查只對全域宣告涵蓋的 spine 內容頁套用；非 spine 的文字目錄不再被當成缺少 viewport 的固定頁，避免因此移除整本書的 `pre-paginated` 宣告。既有文字流動書誤宣告修復仍保留。

目錄中的同檔案片段入口與整章入口不互相去重，例如分篇 `chapter.xhtml#group` 與首章 `chapter.xhtml` 均保留；只有真正相同目標的分組入口才沿用既有保留分組文字的處理。

非標準 XHTML `cc` 卷名容器會改成合法 `span.epub223-cc`，原文字、錨點、類別與內嵌樣式保留；CSS 的 cc 型別選擇器同步調整，避免標籤修好卻失去卷名樣式。參照 Calibre／Sigil 修復後重查結構與連結的原則，未移植第三方程式碼。

完整獨立段落「原版未篡改內容請移至 #官!網……退出瀏覽器閱讀模式」以已核實繁簡文字指紋移除；保留尾文、引用及錨點，不按「廣告」或「攔截」等一般字詞刪文。沿用 Calibre／Sigil 保留有效連結與正文的原則，未移植第三方程式碼。

完整「附：【本作品來自網際網路及出版圖書,本人不做任何負責】內容版權歸作者所有」可精確清除（支援繁簡）；引述、含錨點／連結或相鄰尾文的段落保留，不依「版權」等一般字詞刪文。

EPUB2 的 NCX 轉 EPUB3 目錄時，spine 路徑核對與 NCX 重建均保留章內片段錨點；同檔案的不同小節不去重，只有完全相同目標才沿用去重。頁碼入口也保留片段；缺失錨點仍交由既有引用檢查，不以移除所有錨點掩蓋問題。依 [Calibre 目錄與連結檢查](https://manual.calibre-ebook.com/en/edit.html) 及 Sigil 保留有效導覽後驗證的原則處理，未移植第三方程式碼。

正式目錄的章內錨點不會使同檔案的正文地標或頁碼入口被當成重複連結刪除；保留原有語意導覽與文字。精確清除完整「更多精彩熱門日本輕小說、動漫小說，輕小說文庫(http://www.wenku8.com) 為你一網打盡！」來源宣傳（含繁簡、HTTP/HTTPS及com/cn變體），保留引述、正文提及、署名、錨點／連結及尾文，不依網址關鍵字批次刪文。

完整「請收藏本站：https://.bg60。筆趣閣手機版：https://m.bg60」來源頁尾可精確清除，支援繁簡與跨行內標籤；不刪正文引用、不完整句、其他網址或含錨點／連結的段落，並保留尾文。

唯一正式 nav、且沒有 NCX 的 EPUB3，只在兩個同層相鄰目錄連號中間，補入 spine 已存在、首段明列正確章號且後面有正文的單一漏列章節。保留正文、原目錄層級及其他入口；缺檔、空章、跨層、章內錨點、非連號及非線性內容不猜補。沿用 [Calibre 目錄編輯](https://manual.calibre-ebook.com/edit.html#editing-the-table-of-contents) 的依實際章節建立入口、保留內容後重新驗證原則，未移植第三方程式碼。

舊鳳鳴軒文字版只清除完整作品集標頭、完整字級／背景色選單及宣傳分隔行；錄入／校對署名、正文提及、引述與不完整片段保留，不依網站名稱批次刪正文。

ZIP 資源名含包內父目錄段（如 `OEBPS/../cover.jpg`）時，僅在正規化後仍位於書籍根目錄時修復；跳出根目錄及內容衝突均在寫入前拒絕。只有位元組完全相同的點陣圖別名才可各自保留並安全改名，不覆寫或刪除圖片；文字／SVG 等資源衝突仍拒絕。

僅清除已核實的兩種完整鞋款／名牌販售宣傳段落（NIKE、ADIDAS 通通1200及固定品牌串）；正文品牌提及、引述與錄入署名保留，不用品牌關鍵字批次刪文。

OPF manifest 的 item 不接受 `width`／`height`；僅移除這兩個未加命名空間的非法屬性，保留圖片檔、引用、XHTML 上的合法尺寸與版面，不猜改圖片。

只清除非法的私有 `layout-blank` property，保留空頁本身、spine 順序、左右跨頁與固定版面設定及未知擴充。依 [W3C itemref property](https://www.w3.org/TR/epub-33/#sec-itemref-elem) 核對，沿用 Calibre Check book 的先定位、保留內容、修復再驗證原則。

空白 `epub:footnote` 不是有效屬性，修復只移除空屬性；href、註腳文字及有效 `epub:type` 均保留，非空未知值不猜測。語意依 [W3C EPUB 結構語意](https://www.w3.org/TR/epub-33/#sec-xhtml-extensions) 核對。

原閱讀順序只剩封面／版權頁時，只有原 nav 完整涵蓋所有非 nav XHTML 才按原目錄順序重建 spine；不完整目錄不猜測補章。沿用 Calibre Check book 的引用核對、修復、再驗證原則，不移植第三方程式碼。

清除 XHTML body 不相容的舊式 `link`、`vlink`、`alink` 屬性，保留正文與實際連結。只有 IDPF 字型混淆清單明確引用且 MIME 錯標的資源才改為字型類型，字型檔與混淆設定不變；不把任意 `.dat` 或其他加密資源猜成字型。

非圖片 manifest 項目不能使用 `cover-image`；修復只移除該非法旗標，保留 XHTML 封面頁、圖片、spine 與其他屬性，不猜測缺少的封面圖。沿用 [Calibre 封面頁與封面圖分開標示](https://manual.calibre-ebook.com/edit.html#marking-the-cover) 的原則，未移植第三方程式碼。

重複 `cover-image` 若無唯一 metadata 指定，只在所有候選圖片位元組完全相同時清除多餘封面標記；不刪圖片、不改正文引用或其他 property。不同圖片保持原狀，交由人工確認，不猜封面。沿用 [Calibre 封面標示及書籍檢查](https://manual.calibre-ebook.com/edit.html#marking-the-cover) 的先確認封面、再修復與驗證原則。

XHTML 的 `aria-labelledby`／`aria-describedby` 必須指向同一文件的實際 ID；修復只清除失效引用，保留有效引用、其他輔助標籤與正文，不猜測不存在標籤應指向哪一段。沿用 [Calibre Check book](https://manual.calibre-ebook.com/edit.html#checking-the-book) 的檢查引用、修復、再驗證原則，未移植第三方程式碼。

只清除有效 JSON 且所有網址均為空的 `calibre:author_link_map` 私有快取；非空作者網址與未知 JSON 保留，正式作者及 Calibre DB 自訂欄位不變。

PDF 轉檔頁面 head 內完整的「下載器購買請聯繫作者 QQxxxxxx 或者微信xxxxxxx」占位廣告會精確清理：污染 title 改為「正文」、污染 meta 移除；正文、圖片及正常作者欄不變，不依一般 QQ／微信字樣刪除內容。沿用 Calibre Editor 檢查後修復並重新驗證的安全原則。

可讀文字轉換尊重明確的 XHTML `translate="no"`（含子元素、可讀屬性；不含元素外尾文）。經人工確認的日文姓名、史料原文與簡體字形分析可用此標準屬性保留；不自動猜測哪些引句應排除。

簡轉臺灣正體逐一處理含明確簡體的可讀欄位，涵蓋正文、章名、nav／NCX、書目及可讀屬性；偵測由共享 zhTranslate 的 OpenCC 字典生成，不再使用漏字的人工短清單。其他正體段落、日文引用、CSS／程式與資源路徑保留，不全書盲目重轉。文字詞彙仍唯一由共享 zhTranslate 處理；明確要求轉換時，共享轉換器缺失或例外會中止，不會靜默略過。

CSS 缺資源檢查同時處理外部樣式表、XHTML 內嵌 `style` 與行內樣式，依各自文件位置解析相對路徑；有可靠同類型檔案才修正路徑，確實不存在的裝飾圖引用改為 `none`。保留正文、現有圖片及遠端 URL，輸出仍需外部 EPUBCheck；沿用 [Calibre Check book](https://manual.calibre-ebook.com/edit.html#checking-the-book) 的檢查引用後修復並重新驗證原則。

第二份舊目錄仍保留指向實際 spine 正文的有效連結與章內錨點；缺頁、非正文及指回正式 nav 的失效導覽只移除 href、保留文字，不為格式通過清掉有效導航。

缺資源比對禁止跨資源類型，避免把缺少的 `Copyright.xhtml` 改指同名 `Copyright.css`。只有同類型的實際檔案才能作為替代；無可靠正文目標時保留文字，缺頁本身仍須由外部內容回讀判斷。此修復沿用 [Calibre Check book](https://manual.calibre-ebook.com/edit.html#checking-the-book) 的檢查與重新驗證原則，不將 CSS 當成閱讀章節。

周讀／「幸福的味道」清理限定完整行行／QQ 2338856113／d716-716／ireadweek 導流段落。整頁刪除還須同時命中人工核准的全文文字指紋與 QR 圖片雜湊；有任何正文、署名或不同圖片即保留。共用圖、封面及 CSS 引用保留，OPF、spine 與目錄同步更新。

僅清理已確認的完整「最新電子書免費分享社群，群主 V 信 1107308023」括號導流標記；支援正簡文字與空白，保留前後正文、署名、引號內引用及其他群號，不依一般「分享社群」關鍵字刪除。

完整星號包裹的 WenKu8.cn／WenKu8.com 網站標頭視為來源宣傳；普通文庫名稱、網址提及與正文引用保留。
論壇網域同頁的完整「本文僅供個人學習交流使用」、「如需轉載請經過本人／翻譯本人同意」與「推薦使用『多看閱讀』」免責／宣傳可精確清除；無論壇網域、引述、含錨點／連結或相鄰尾文時保留，作者／譯者署名與後記不刪。

「（Free書分享更多搜雅書）」僅匹配完整已核實導流括號；兼容正簡字及相鄰兩段的 PDF 拆行，不刪除圖說正文、一般引用或不完整片段。
同樣只精確移除「（更d書f享搜索雅書.YabooK）」混淆字導流括號，不以一般站名提及刪正文。
亦精確移除「（此書更多分享搜索@雅書B）」完整正簡字導流括號，保留引用與周圍正文。

來源清理涵蓋已確認的 xxdzs2 完整下載宣傳句、奇書網完整免責句，以及 `☆奇書網のWww.qinkan.net★`、括號反引號及雙星號的精確插入標記；不以一般網址或關鍵字刪除正文，完整引句與署名保留。

來源段落清理僅匹配已確認的完整下載免責、指定 QQ／ireadweek 導流、付費掃碼插入句及特定 App 推廣句；保留署名、教材 QR 提示及正文引用。
「滿屋書香」只精確清除包含 sisijuan2012、QQ 151680600 與指定簡書網址的完整已核實段落；保留不同帳號、一般提及、引用與相鄰正文。
混在註解後的滿屋書香廣告，另須完整區塊文字及逐張人工核准的圖片雜湊全部匹配，且區塊沒有錨點才移除；前方正文註解、未知圖片、封面及其他章節共用圖片保留。

純圖片來源宣傳頁只比對人工確認的 Kmoe／Koobone 宣傳 PNG 之 SHA-256，不依檔名或 OCR 關鍵字刪頁。僅清除沒有正文、只含已知宣傳圖的 XHTML 與其 OPF／spine／目錄引用；封面、含正文的頁面及仍被正文或 CSS 使用的圖片均保留。

宣傳圖清理略過 OPF manifest 的 XML 註解，保持原註解內容，不因非元素節點中止修復。

`--convert-chinese s2tw` 只轉換有明確簡體字的可讀文字欄位，已為正體的段落與含假名的日文引句、〈〉／書名號／括號引用保留；詞彙和標點仍使用 zhTranslate，不改資源路徑或程式碼。

解壓會先為 Windows 不安全檔名與大小寫碰撞分配唯一名稱，再更新 OPF／NCX／XHTML／CSS 相對引用；不使用會將 `*`、`:` 等字元清除而覆蓋章節的 `extractall`。重複 ZIP 成員、路徑穿越及不安全目錄會明確失敗並保留輸入檔。此保護由 EPUB2 轉換、EPUB3 修復及 Kindle 副本共用；最終仍應比對章節及正文保存，不能只看 EPUBCheck。參考 [Python ZIP 解壓行為](https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile.extract) 與 [Calibre 改名引用同步](https://manual.calibre-ebook.com/edit.html#renaming-files) 的安全原則。

XHTML head 重複標題會保留首個非空 `<title>`；全部為空時沿用文件名補標題的既有規則。只清理 head，不更動正文，以免多餘空標題導致 EPUBCheck `RSC-005`；EPUB2 轉換與 EPUB3 pure-repair 共用。修復採 [Calibre Check book](https://manual.calibre-ebook.com/edit.html#checking-the-book) 的先檢查、修復、再驗證思路，未移植第三方程式碼。

格式修復會辨識內容以 `%PDF-` 開頭、但誤標成 CSS 的二進位資源，修正 OPF media type 並避免將其當成文字樣式表改寫。

既有來源廣告清理也會移除 677txt 完整下載推薦句及其緊鄰的每日更新宣傳句，保留一般引用與書籍內容。
含 lightnovel.cn／fun／app／life 或 sosg.net 的來源署名頁只清除完整論壇網址、下載免責與轉載宣傳段落；支援已核對的輕書架聯合免責及跨換行合併宣告，作者、譯者、錄入署名及正文後記保留。
同一精確宣傳句清理涵蓋 tsdm 網址、LK 與 TSDM 免責、yidm 六條下載宣告，以及選書網 xuanshu 與 qinkan 格式下載頁尾；須有明確來源網址及完整句型，不刪作者、譯者、出版資訊或正文引用。
既有來源廣告清理也會移除完整的 ePUBw「本書由…整理，…提供最新最全的優質電子書下載」宣傳段落，支援繁簡及跨行內標籤；不因正文提及網站名就刪除整段。

這是把原本的 Sigil `ePub3-itizer` plugin 核心整理成獨立 CLI 專案的版本。

用途很單純：

- 把 EPUB2 轉成 EPUB3
- 支援單一 EPUB 檔轉換
- 支援整個資料夾批次轉換
- 不依賴 Sigil 介面

## 功能

- XHTML 的 `a`、`ins`、`del` 依 HTML 透明內容模型繼承外層限制；
  合法的區塊連結內 `p`、`hr` 保留，不再一律改成 `span`，避免目錄段落併行。
  若外層仍限制行內內容，則維持必要的結構修復。
  依據：[HTML 透明內容模型](https://html.spec.whatwg.org/multipage/dom.html#transparent-content-models)。

### Kindle 橫排流式副本（選用）

```powershell
python -m epub3itizer.kindle "原書.epub" "Kindle橫排.epub" --language zh-Hant
```

此入口額外使用 `tinycss2`（未安裝時執行 `python -m pip install tinycss2`），
僅適用 EPUB3 文字書，普通轉換／`--repair-only` 不會自動套用。
它將直排 CSS 改為橫排、spine 改為由左至右、取消混合固定頁面，
把無裁切的單圖 SVG 包裝改成可縮放插圖。`--language` 只在確認內容語言後指定，
同步 OPF 與 XHTML 根元素，不改內文局部外語標記。
不接受輸入輸出同檔；全書固定版面、絕對定位或複雜 SVG 會停止，不能拿來自動重排漫畫。
輸出後仍應執行 EPUBCheck，並重新傳送至 Kindle 確認能否調整字級。

相容性依據為 [Amazon 正體中文出版方向說明](https://kdp.amazon.com/en_US/help/topic/G27T64E65VM6JWKK)
及 [流式排版指引](https://kdp.amazon.com/en_US/help/topic/GPNJPYK298J8TRRV)。
KDP 與 Send-to-Kindle 並非同一服務，這些是相容性參考，不是雲端驗收保證。
先檢視 calibre EPUB 匯入與封面處理的參考思路，未移植其程式碼；此模式屬選用排版轉換，
不是將合法的直排或混合版面一律當成 EPUB 格式錯誤。

### Kindle 直排相容副本（選用）

```powershell
python -m epub3itizer.kindle "原書.epub" "Kindle直排.epub" --keep-vertical --language zh-Hant
```

這是針對實測被 Send-to-Kindle 拒絕、且 OPF `spine` 含
`page-progression-direction="rtl"` 的中文直排 EPUB3。它只移除該 RTL 宣告；
保留 `vertical-rl`、固定頁／跨頁設定、SVG、viewport、圖片與正文。普通修復不會套用，
也不覆寫原書，因為這會改變 EPUB 宣告的閱讀方向。輸出仍須通過 EPUBCheck 並實際傳送確認。

### 一般轉換與修復

- XHTML 命名空間內的 Pubu 私有 `<ploc>` 位置標記會改為標準 `<span>`，不刪除數字或內容，保留有效錨點與子元素；其他命名空間不改。沿用已知非標準標籤正規化，採 Calibre／Sigil 先修復再檢查的安全流程，不移植第三方程式碼。
- 多個 `cover-image` 衝突僅在 OPF 既有封面 metadata 唯一指定其中一張圖片時自動排除其他封面標記；不刪圖片，不猜測不明確的封面。

- 保留原本的 EPUB2 -> EPUB3 轉換邏輯
- EPUB2→3 與 `--repair-only` 會檢查正文根元素及實際引用的 CSS：全書正文明確為橫排時移除 OPF spine 的 `page-progression-direction="rtl"`，不修改正文、CSS、圖片或閱讀順序；直排、混合排版、文字 RTL、只有圖片或無法確認樣式時保留原宣告。此規則不保證單獨排除 Kindle E016 的其他因素（例如 SVG）。
- 直接從命令列處理單檔
- 資料夾批次轉換
- 可遞迴掃描子資料夾
- 轉換時保留原始資料夾結構
- 可搭配 `epubCheck` 驗證輸出檔
- 可選擇把 EPUB 內可讀文字從簡體中文轉成臺灣正體中文
- 轉換與修復流程會清理常見閱讀器或平台殘留，例如 `calibre_bookmarks.txt`、`Provider.txt`，以及 EPUBCheck 不友善或閱讀器私有的 CSS 宣告如 `text-combine-horizontal: all;`、`text-combine: horizontal;`、`text-spacing-trim: trim-start;`、`duokan-text-indent: 0;`
- XHTML 清理會移除少數明確來源廣告，例如 `請看小說網` / `qinkan.net`、`言情兔` / `yanqingtu.com` 宣傳短段與正文中的站台浮水印；段落規則需同時命中站台識別與廣告語，避免誤刪正文
- XHTML 清理會移除與元素同名、或空值且名稱像 HTML 標籤名的非法屬性，例如 `<div div="">`、`<div i="">`，這類常見於轉檔器錯把破碎標籤殘片保留下來的情況
- XHTML 樣式表 `<link>` 若將資源路徑錯寫於 `src`、卻未寫 `href`，會保留路徑並移至標準 `href` 屬性，避免 EPUBCheck 將 `src` 視為非法屬性
- XHTML 正文的舊式 `<image>` 元素會改為標準 `<img>`，但 SVG 命名空間內的 `<image>` 保留；修復時也會依圖檔檔頭更正錯置的 JPEG／PNG／GIF／WebP／TIFF 副檔名並回寫所有引用
- XHTML 清理會移除 AZW3/Calibre 轉檔後掉進正文的孤兒標籤殘片，例如 `id="_idParaDest..." class="..." aid="..."&gt;` 或 `d="footnote-..." class="_idFootnote" ...&gt;`，並移除真正元素的 `aid` 私有屬性；完整跳脫標籤及 `code`／`pre`／`kbd`／`samp` 內程式範例原文保留，不把其屬性字串誤當殘片。這類問題可能通過 EPUBCheck，但會在閱讀器中顯示成錯誤內文
- XHTML 清理會移除舊轉檔器加在圖片上的私有 `active="true"` 屬性，保留圖片 `src`、`alt`、`class` 與正文，避免 EPUBCheck `RSC-005`
- XHTML 清理會移除已棄用的 ARIA `role="doc-*"` 註腳角色，例如 `doc-endnote`、`doc-endnotes`、`doc-backlink`，但保留 EPUB 標準的 `epub:type="footnote"`／`footnotes` 與其他非 `doc-*` ARIA 角色，避免 EPUBCheck `RSC-017` 警告
- 目錄頁修復會整理空 `<dd/>` 的舊式 `<dl>` 目錄、把官方 nav 檔中只有 `<div><ul>` 的普通目錄補成 EPUB3 需要的 `<nav epub:type="toc">`，並攤平製作器誤產生的單鏈巢狀 nav，讓章節維持可點擊且階層合理
- 修復 SVG 圖像式目錄內遺失或重複資料夾的 `xlink:href` 章節連結，依實際 XHTML 檔案回寫為正確相對路徑
- CSS 清理會移除重複屬性宣告，例如重複的 `font-weight`、`border-top`、`border-bottom`、`border-left`、`border-right`；同名屬性保留最後一次宣告，以符合 CSS cascade 語意並降低 Sigil 檢查書本警告
- XHTML 嚴格解析失敗時，先定位孤立或缺少的 `p` 邊界並嘗試嚴格重解析，避免 recover 截斷後續文字；原始文字、屬性、註解與外來命名空間不重序列化，簡轉繁沿用同一安全解析路徑。
- 修復流程會整理官方 `nav.xhtml`；父層若與子項目具有相同目標且造成閱讀順序問題，可降級為純文字。僅指向相同 spine 檔案、但錨點不同的分組入口仍保留，不以檔案相同判定重複；同一檔案內 fragment 後的裸連結沿用既有清理，保留子章節連結。
- OPF 清理會保留 manifest/spine 使用中的資源 id，並將 metadata 中撞名的 `id` 改成安全名稱，避免 EPUBCheck 回報 `Duplicate "title"` 等 XML id 衝突
- OPF 清理會移除 0 位元組的 XHTML manifest/spine 項目及其失效目錄連結，避免 EPUBCheck `RSC-016` 的空文件解析錯誤
- EPUB2 OPF 中緊接文字的 XML 註解（例如 `<!--accessibility options-->`）會正確略過，不會誤把後續 manifest／spine 包入 metadata。

## 專案結構

```text
convert_epub3.py        # 舊入口相容包裝
epub3itizer/            # CLI 主程式
  __main__.py
  cli.py
  compat.py
  conversion.py
src/                    # 原始轉換輔助模組
tests/                  # 測試資料
```

## 需求

- Python
- `lxml`

如果你是直接從原始碼執行，轉換功能本身通常只需要先安裝 `lxml`。

```bash
pip install lxml
```

如果要使用簡轉正參數，另需安裝 `opencc-python-reimplemented`。

```bash
pip install opencc-python-reimplemented
```

如果你想在轉換後額外跑 `epubCheck` 驗證，才需要 Java 8+ 或可執行 `java -jar` 的環境。

## 使用方式

### 單一檔案轉換

```bash
python convert_epub3.py "D:\project\epub223\testFile\input.epub" -o "D:\project\epub223\testFile\output.epub"
```

也可以直接用模組入口：

```bash
python -m epub3itizer "D:\project\epub223\testFile\input.epub" -o "D:\project\epub223\testFile\output.epub"
```

### 簡體轉臺灣正體

預設不會改動書內文字。需要簡轉正時，明確加上 `--convert-chinese s2tw`。

```bash
python -m epub3itizer "D:\project\epub223\testFile\input.epub" -o "D:\project\epub223\testFile\output.epub" --convert-chinese s2tw
```

這個選項會轉換 EPUB 內 XHTML、OPF、NCX、XML 的可讀文字與 `title`、`alt`、`content` 等文字屬性，但不會改 `href`、`src`、`id`、CSS、URL 或 script/style 內容。
同時會參考 `Hopkins1/TradSimpChinese` 的引號處理方式，將西式彎引號 `“”‘’` 轉成臺灣正體常用的 `「」『』`。

轉換邏輯使用 `D:\github\zhTranslate` 共用文字轉換層：

- 使用 `zhTranslate` 的 `s2tw_converter.Converter`。
- 套用 `D:\github\zhTranslate\src\s2tw_converter\custom_replacements.tsv` 裡的共用自訂替換。
- 若尚未安裝 `zhTranslate`，程式會嘗試從 `D:\github\zhTranslate\src` 載入。

EPUB 結構安全仍由 `epub223` 負責：只轉換可讀文字與允許的文字屬性，不會把整份 XHTML/XML 當純文字轉換。

### 單獨修復 EPUB

修復亦會以 OPF 書名補齊 NCX 中完整等於 `[此处填写标题]`／`[此處填寫標題]` 的占位標題；不替換有效標題，也不更動章節與連結。

來源宣傳清理亦包含逐字確認的《九重紫》首頁求票完整段落；引號內引用及相鄰正文保留，不泛化為含「廣告」即刪除。

首頁「典盡春衣畫流年／75687572」群號導流只清除完整框線內十一段，保留後方書名、作者、簡介與正文；缺段、其他群號、錨點或正文混入時保留，不以微信或群組關鍵字批次刪文。

XHTML 的空 `<divclass __contentadv_=""/>` 已確認是廣告占位殘留，只移除無正文、無子元素且無其他屬性的完整節點；保留尾端文字、錨點、未知變體與其他命名空間，不猜測一般標籤拼字。

Word 的 XHTML 日期／量度包裝 `chsdate`、`chmetcnv` 改成標準 `span`，保留可見日期、數字、ID、class 與內部連結，清除包裝上的非標準屬性；其他命名空間不改。精確宣傳指紋遇到 XML 註解時不匹配，不影響後續標題及章節正規化。

如果你已經有 EPUB3 檔，只想套用同一套修復規則，不需要重新做 EPUB2 -> EPUB3 轉換，可以用修復模式：

```bash
python -m epub3itizer --repair-only "D:\project\epub223\testFile\input.epub" -o "D:\project\epub223\testFile\output_repaired.epub"
```

修復模式也可以搭配簡轉正：

```bash
python -m epub3itizer --repair-only "D:\project\epub223\testFile\input.epub" -o "D:\project\epub223\testFile\output_repaired.epub" --convert-chinese s2tw
```

資料夾模式也支援批次修復：

```bash
python -m epub3itizer --repair-only "D:\project\epub223\testFile\books" --recursive --output-dir "D:\project\epub223\testFile\books_repaired"
```

### 整個資料夾批次轉換

```bash
python -m epub3itizer "D:\project\epub223\epub2" --recursive --output-dir "D:\project\epub223\epub3"
```

如果你不指定 `--output-dir`，預設會輸出到：

```text
原資料夾名稱_epub3
```

例如：

```text
D:\project\epub223\epub2  ->  D:\project\epub223\epub2_epub3
```

### 常用參數

- `-o, --output`：單檔輸出路徑
- `--output-dir`：批次模式輸出資料夾
- `--recursive`：遞迴掃描子資料夾
- `--suffix`：批次輸出檔名後綴，轉換預設是 `_epub3`，修復預設是 `_repaired`
- `--overwrite`：覆蓋已存在的輸出檔
- `--repair-only`：只執行可重用的 EPUB 修復流程，不做 EPUB2 -> EPUB3 轉換
- `--convert-chinese {none,s2tw}`：可選簡轉正；預設 `none`

## 驗證

完成後可用 `epubCheck` 驗證：

```bash
java -jar "C:\PortableApps\[epub] epubCheck\epubcheck.jar" "D:\project\epub223\testFile\output.epub"
```

本專案目前已實測輸出可通過 `epubCheck`，顯示 `0 errors / 0 warnings`。

修復流程會正規化 OPF metadata 裡的語言碼，例如把 `zh_TW` 改成合法的 `zh-TW`，避免 EPUBCheck 回報 `OPF-092`。

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

### Kindle 相容性處理界線

一般轉換與 `--repair-only` 都會沿用 UTF-8 輸出、資源路徑與 manifest 修復，
並將指向實際且唯一 `<body id="…">` 的本機連結改連到該頁面；正文、body ID、
段落／註腳錨點保留。支援相對路徑、URL 編碼與同頁連結；外部 URL、含查詢參數、
重複 ID、無法解析的 XML 與含 `xml:base` 或 HTML `<base>` 的文件不套用此規則。

不照搬第三方的全部修復：不將未知語言猜成英文，也不為了消除錯誤直接刪除
缺檔引用或不存在的段落錨點。這些規則只能處理已知問題；EPUBCheck 為外部規範驗證，
Kindle 轉換仍須另以官方 Previewer 驗證，不能保證 Send-to-Kindle 接受。

## 與 Sigil plugin 版的差異

除了 UI 之外，主要差異是：

- CLI 版直接讀取檔案系統，不需要先開 Sigil
- CLI 版輸出路徑由命令列參數控制
- CLI 版多了批次資料夾轉換
- plugin 版依賴 Sigil 的書籍狀態、選單與儲存流程
- 核心轉換邏輯仍然共用同一套程式碼

換句話說，這個 CLI 版是把原本 plugin 的核心轉換能力抽出來，讓它可以獨立跑，也比較適合大量 EPUB2 檔案的批次處理。

## 專案與授權

閱讀順序修復只排除 manifest 明確標示 `properties="nav"` 的正式導覽文件；同名舊目錄或正文頁仍保留，不以 `nav.xhtml` 檔名判定可移除。

此專案由 [SamLaio](https://github.com/SamLaio) 維護。

程式源引自以下上游專案：

- [kevinhendricks/ePub3-itizer](https://github.com/kevinhendricks/ePub3-itizer)
- [Sigil-Ebook/Sigil](https://github.com/Sigil-Ebook/Sigil)

它改寫自早期的 Sigil `ePub3-itizer` 核心，但目前已經是獨立的 CLI 工具。

授權採 GNU General Public License v3.0，完整內容請見 [`COPYING.txt`](COPYING.txt)。

簡轉繁會保留明確標示 `lang="ja"` 或 `xml:lang="ja"` 的日文（含 ja-JP），涵蓋子節點及可讀屬性；元素外的中文尾文仍正常轉換。

後記前的已知輕之國度／天使動漫框線宣傳區塊只在完整邊界與全部行型態可確認時清理；保留正式署名、後記、正文、圖片及錨點。不因單一來源關鍵字命中而刪除整段。

## 2026-10-30：精確末尾錄入署名

只移除末尾緊接純文字 END 的獨立「兔子家族製作／制作」段落；兩段僅允許class屬性，不得有子節點或非空尾文。保留正文提及、引述、正式製作資訊與後記，新增正反例及冪等測試。

## 2026-10-30：完整失聯目錄的精確重建

當至少兩項且全部toc連結都遺失href，僅在全部標題均能精確對應正文最高層級的唯一同名標題，且目標依spine與章內順序遞增、不重複時，重建連結及必要的唯一錨點；保留目錄階層與全部標籤。參考文獻同名小標不覆蓋主要標題，歧義、順序不符及已有連結均不套用，補正反例及冪等測試。

## 2026-10-31：核實錄入組頁面指紋

增加同事題材小說之完整錄入組頁指紋；仍須全文精確相符且無圖片、錨點或額外正文才移除，沿用manifest／spine／目錄同步清理，擴充正反例測試。

- 2026-10-31：核准全文指紋製作頁允許無錨點的 b 粗體標記，補實際書籍版型回歸；完整指紋、封面與正文安全限制不變。

- 2026-11-01：無副檔名資源僅在明確UTF-8 @charset宣告、可解析且含樣式規則時辨識為text/css，修正Sigil未知MIME警告；保留資源內容與路徑，不猜測一般文字或二進位檔。補正反例與manifest回歸。
