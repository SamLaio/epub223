# Change Log


## 未發布

### 文件

- 重整 README：先說明用途、安裝與快速開始，依操作情境集中詳細用法、輸出與限制；更新紀錄集中於 CHANGELOG，不再插入使用說明。

## 1.9 - 2026-11-01

- 修正同步朗讀SMIL類型及時長、保留合法OPF scheme與media refinement，保護固定版面與日文原文。
- 保留不同目錄目標，僅在完整唯一標題證據成立時重建全失聯目錄；保留cc卷名樣式。
- 以精確指紋與安全邊界清理已核實來源宣傳；辨識無副檔名的明確UTF-8 CSS，避免Sigil未知媒體類型警告。
- 381 項回歸測試通過。

### 詳細修正紀錄

### 開發紀錄：2026-10-29

- 官網導流連結被上游清理成 span 時，仍須完整導流句與已核准純QR圖雙重吻合才移除；若仍有連結，目標必須符合鏡文學官網。未知圖片與不同連結保留。

- 宣傳頁掃描保留 XML 註解，不把 body 的註解節點交給文字迭代器；完整宣傳尾段中混入註解時停止判定，補實書觸發的無核准圖片回歸。

- 依完整全文指紋移除已核實的獨立錄入組資訊頁，同步清除 manifest／spine／導覽引用；正文、正式署名、圖片或錨點混入時保留。
- 鏡文學延伸閱讀段落須同時符合完整導流句、官網連結及核准純 QR 圖指紋才移除；共用圖像保留，另附番外／試閱正文保留。補安全邊界及冪等回歸。

### 開發紀錄：2026-10-26

- OPF `meta` 保留 EPUB3 合法的 `scheme` 屬性（例如作者角色的 `marc:relators`），不在 pure-repair 或 EPUB2→3 後清理時誤刪詞彙定義；非法屬性仍移除，補正文保全與冪等回歸。

- 保留 EPUB2 既有 `media:*` 同步朗讀書目及指向 manifest 的合法時長 refinement；依實際 SMIL 補正 MIME 與缺少的逐檔時長，補齊全書時長或使其與逐檔總和一致，不改音訊、同步點、正文或既有逐檔時長。缺 clipEnd、倒序或未知時間格式時停止，不猜音訊長度。補文字保全、單位、冪等及不安全輸入等13項回歸測試。

- 作者後記前完整框線內的已知輕之國度／天使動漫錄入宣傳區塊，僅在標頭、網址、行標籤及邊界全部符合時移除來源標頭與錄入資訊；保留作者、插畫、譯者署名與後記。含正文、錨點、未知行或不完整框線時不套用，補安全反例與冪等測試。

### 開發紀錄：2026-10-25

- 簡轉繁保留明確標註 `lang="ja"`／`xml:lang="ja"`（含 ja-JP）的日文元素、屬性與子節點；元素外的中文尾文仍轉換。避免日文政黨索引與參考書名被誤轉，補巢狀、尾文、屬性與冪等測試。

### 開發紀錄：2026-10-24

- 全域固定版面 viewport 檢查限於 spine 內容頁，避免非 spine 的 nav 目錄缺少 viewport 而誤移除整本 `pre-paginated` 宣告；保留原頁圖、頁數及導覽，並新增回歸測試。真正文字內容頁的既有誤宣告清理保持不變。

- 修正目錄去重誤刪葉節點：分篇的 `chapter.xhtml#group` 與首章 `chapter.xhtml` 為不同入口，兩者及原文字皆保留；不再因同一 spine 檔案先出現片段連結而移除整章入口。補分篇／首章連結及冪等回歸。

- 非標準 XHTML `cc` 卷名容器改為 `span.epub223-cc`，同步轉換 CSS 的 cc 型別選擇器（含條件規則與選擇器函式），保留文字、錨點、類別及內嵌樣式。類別／ID／屬性、宣告內容及外部命名空間不誤轉，補樣式保全與冪等回歸。

- 精確清除完整獨立段落「原版未篡改內容請移至 #官!網……退出瀏覽器閱讀模式」導流指紋，支援繁簡；保留尾文、引用、錨點及混入正文的變體，補冪等與保全測試。


### 開發紀錄：2026-10-30：精確末尾錄入署名

只移除末尾緊接純文字 END 的獨立「兔子家族製作／制作」段落；兩段僅允許class屬性，不得有子節點或非空尾文。保留正文提及、引述、正式製作資訊與後記，新增正反例及冪等測試。

### 開發紀錄：2026-10-30：完整失聯目錄的精確重建

當至少兩項且全部toc連結都遺失href，僅在全部標題均能精確對應正文最高層級的唯一同名標題，且目標依spine與章內順序遞增、不重複時，重建連結及必要的唯一錨點；保留目錄階層與全部標籤。參考文獻同名小標不覆蓋主要標題，歧義、順序不符及已有連結均不套用，補正反例及冪等測試。

### 開發紀錄：2026-10-31：核實錄入組頁面指紋

增加同事題材小說之完整錄入組頁指紋；仍須全文精確相符且無圖片、錨點或額外正文才移除，沿用manifest／spine／目錄同步清理，擴充正反例測試。

- 2026-10-31：核准全文指紋製作頁允許無錨點的 b 粗體標記，補實際書籍版型回歸；完整指紋、封面與正文安全限制不變。

- 2026-11-01：無副檔名資源僅在明確UTF-8 @charset宣告、可解析且含樣式規則時辨識為text/css，修正Sigil未知MIME警告；保留資源內容與路徑，不猜測一般文字或二進位檔。補正反例與manifest回歸。

## 1.8 - 2026-10-23

### 修正紀錄 - 2026-10-23

- 精確清除完整「附：【本作品來自網際網路及出版圖書,本人不做任何負責】內容版權歸作者所有」來源免責段落，支援繁簡。引用、署名、正文、錨點／連結及相鄰尾文保留；補繁簡正反例與冪等測試，沿用 Calibre 備份及逐檔比文後驗證原則，不移植第三方程式碼。
- 補齊論壇網域同頁的完整「本文僅供個人學習交流使用」、「如需轉載請經過本人／翻譯本人同意」與「推薦使用『多看閱讀』」免責／宣傳段落。僅精確段落且無錨點、連結或相鄰尾文時清除，保留署名、正文引用及作者後記；新增正反例與冪等測試，沿用 Calibre 備份及保文後重新驗證原則，未移植第三方程式碼。
- 修正 EPUB2→3 的 spine 目標篩選與 NCX 重建丟棄片段錨點、把同檔不同小節視為重複的問題。保留章節、子節及頁碼入口，只有完全相同目標才去重；既有資源與缺失錨點修復仍照常驗證。補正路徑、大小寫／副檔名修復、NCX 往返、分層 nav 與冪等回歸；依 Calibre 目錄連結核對及 Sigil 保留內容後驗證的安全原則，不移植第三方程式碼。

### 修正紀錄 - 2026-10-22

- 修正目錄錨點去重誤刪同檔正文地標與頁碼入口；去重只限正式目錄，不跨不同語意導覽。補連結、文字及冪等回歸，沿用Calibre目錄核對及Sigil保留內容後驗證的安全原則。
- 加入完整輕小說文庫導流句的精確繁簡指紋；保留引述、不完整句、正文提及、署名、有效錨點／連結及尾文，不以網站名稱擴大刪文。補正反例與冪等測試，未移植第三方程式碼。

### 修正紀錄 - 2026-10-17

- XHTML 嚴格解析失敗時，先以HTMLParser定位並修正孤立p結尾及缺少p結尾；僅修標籤邊界、嚴格重解析成功後才採用，避免XML recover靜默截斷後續可見文字。簡轉繁共用相同解析路徑；保留原文字、錨點、屬性、註解及SVG，補正反例與冪等測試，借鏡Calibre修復HTML前後核對的安全流程。

- 修正分層目錄把同一檔案內不同章內錨點誤判成重複入口的問題；只有父子連結目標完全相同時才沿用分組降級，保留獨立分組標題、各節連結與正文。補保存連結、文字及冪等回歸；參考 Calibre 先核對目錄目標再驗證的做法，不移植第三方程式碼。

### 修正紀錄 - 2026-10-16

- 補齊 README 與 AGENTS 的四項 Kindle／EPUB 參考專案，新增 `dliedke/Kindle-EPUB-Fix` 與 `w3c/epubcheck`，說明參考範圍、外部驗證角色及相容性限制。

- 納入 `imanubdesigner/epub-kindle-fix` 修復參考與安全處理界線，釐清 `innocenat` 的編碼及 body 錨點用途；沿用既有資源／XML 修復，不猜語言或刪斷鏈掩蓋問題。
- 共用轉換／pure-repair 流程新增唯一 body ID 本機連結正規化，保留正文與段落錨點，補正反例及冪等回歸。

### 修正紀錄 - 2026-10-15

- 精確清除完整「請收藏本站：https://.bg60。筆趣閣手機版：https://m.bg60」殘缺網址頁尾，支援繁簡與跨行內標籤；正文、引用、其他網址、不完整片段、錨點／連結及尾文保留。補正反例與冪等回歸，不以一般網址關鍵字刪文。

- 唯一正式 nav 且無 NCX 時，安全補入同層相鄰連號目錄中間漏列的單一既有章節。需同時核對線性 spine、實際首段章名、前後章號與非空正文；不改正文或猜補缺章。補中文／阿拉伯章號、冪等及十種不安全條件回歸，已有章內錨點入口不重複補列，未知混合數字不猜讀。

### 修正紀錄 - 2026-10-14

- 精確清除鳳鳴軒完整作品集標頭、完整字級／背景色導覽選單及獨家製作宣傳分隔行；正文提及、引用、不完整選單與掃描／校對署名保留。補尾文、錨點、引用及冪等回歸。

- 安全正規化 ZIP 資源名中的包內父目錄段；例如 `OEBPS/../cover.jpg` 還原為根目錄封面。先檢查根目錄逃逸與正規化檔名衝突，拒絕危險封包，不放寬 Windows 非法目錄限制；只有位元組完全相同的點陣圖別名沿用安全改名並保留兩份，不覆寫資源。補封面位元組與引用保存、兩種根目錄逃逸、內容／大小寫衝突及同圖別名回歸。

- 加入兩種完整鞋款／品牌販售宣傳指紋，清除舊文字版電子書夾帶的無關廣告；保留正文品牌提及、引述、錄入署名與尾文。補完整文字、錨點及冪等回歸，沿用 Calibre Check book 先定位、保留內容、再驗證的安全做法，不移植第三方程式碼。

## 1.7 - 2026-10-13

### 修正紀錄 - 2026-10-12

- 新增橫排 spine 修復：依正文 html／body 與引用樣式確認全書橫排後，移除 `page-progression-direction="rtl"`；EPUB2→3 與 EPUB3 pure-repair 共用。直排、混合、文字 RTL、圖片書或未知方向保留，正文、圖片、CSS 與 spine 順序不變。

- 孤兒標籤殘片清理不再誤刪完整跳脫標籤內的屬性；保留程式範例、尾端文字及真正元素ID，原孤兒殘片仍清理。補正文完整性及冪等回歸；借鏡 Calibre 以解析結構與 checkpoint 區分正文的安全原則，不移植第三方程式碼。

- 移除 OPF manifest item 上未加命名空間的非法 `width`／`height`，保留圖片、引用、XHTML 合法尺寸及閱讀順序；補圖片／正文位元組保存與冪等回歸。

- 只清除已確認非法的 `layout-blank` property，保留頁面、資源、spine 順序、左右跨頁、固定版面及其他擴充；不把空頁當廣告刪除。補單獨／混合屬性、原文保存及冪等回歸。

### 修正紀錄 - 2026-10-11

- Word 匯出的 XHTML `chsdate`／`chmetcnv` 已確認為日期與量度包裝，沿用既有非標準標籤流程改成 `span`，保留可見文字、ID、樣式與內部連結；移除其私有 Word 屬性，避免 EPUBCheck 在無主機名稱的 URN 屬性上中斷，其他命名空間不改。補完整內容、連結及冪等回歸。

- 精確首頁宣傳指紋先排除 XML 註解／處理指令，避免對註解呼叫 itertext 導致該章節正規化被略過；保留註解及正文，空白 title 仍由正常格式流程補正。補完整流程回歸。

- 僅移除 XHTML 中空的 `<divclass __contentadv_=""/>` 廣告占位殘留；原正文與尾端文字保存，有內容、子元素、錨點、其他屬性值或其他命名空間時不刪。補安全邊界、文字完整性及冪等回歸。

- 僅清除首頁完整框線包裹的「典盡春衣畫流年／75687572」十一段群號與微信導流；書名、作者、簡介及正文保留，缺段、不同群號、錨點或混入正文一律不刪。補完整邊界、正文保存及冪等回歸；沿用 Calibre 檢查引用與保留 checkpoint 的安全原則。

- 只移除空白的非法 `epub:footnote` 屬性，保留註腳文字、href、ID 與有效 `epub:type`；非空未知值仍回報，不猜語意。補文字／連結保存與冪等回歸。

- 原 spine 只剩封面／版權頁時，僅在原 nav 完整涵蓋所有正文 XHTML 的情況，按目錄順序補回閱讀順序；不按檔名排序，不刪正文，不完整目錄保留待確認。補完整／缺章與冪等回歸。

### 修正紀錄 - 2026-10-10

- 清除 XHTML body 舊式 link/vlink/alink 屬性，保留文字與實際連結；IDPF 字型混淆清單已確認的 .dat 字型只修正錯誤 MIME，不解碼、不改字型位元組或混淆設定。新增保留正文／連結、其他資源及冪等測試。

- 清除逐字確認的《九重紫》首頁前十名求票廣告完整正簡段落；不以「廣告」關鍵字批次刪文，保留引號內引用、前後正文並補冪等回歸。

- NCX `docTitle` 僅在完整等於「[此处填写标题]」或其正體形式時，以 OPF 正式書名補齊；有效標題、章節文字與連結不動。EPUB2→3 與 pure-repair 共用，補正簡占位、有效標題保存與冪等回歸；沿用 Calibre 的目錄與正式書目分開核對原則。

- OPF manifest 的非圖片項目移除非法 `cover-image` 旗標，避免 XHTML 封面頁與真正封面圖被同時標示。文件、圖片、spine 與其他屬性保留；不猜測替代封面，補有／無封面圖及冪等回歸。沿用 Calibre 封面頁與封面圖分開標示的安全原則。

- XHTML 的 `aria-labelledby`／`aria-describedby` 僅保留同一文件中實際存在的 ID；混合引用只清除失效項，全部失效時移除該屬性，保留有效輔助標籤、`aria-label` 與正文。補跨頁 ID 不誤認、有效引用保存及冪等回歸。

- 精確清除完整「滿屋書香／sisijuan2012／QQ 151680600／指定簡書網址」正簡字導流段落；保留一般站名提及、不同帳號、引號內引用與相鄰正文，補冪等回歸。
- 增添逐張核准的滿屋書香宣傳圖雜湊；正文註解後的宣傳尾段須完整文字指紋、所有圖片指紋及無錨點安全邊界同時成立才清除，保留前方註解、未知圖片、封面與共用資源。

- 精確移除「（此書更多分享搜索@雅書B）」完整正簡字來源導流括號；保留引號內引用、周圍正文，補安全邊界與冪等回歸。

- 多張圖片同時標示 `cover-image`，但封面 metadata 無唯一選擇時，僅在所有候選均為圖片且檔案位元組完全相同時保留第一個封面標記。圖片、其他 property、正文與資源引用皆保留；不同圖片仍要求明確封面 metadata，不猜選。補相同圖片、衝突 metadata、安全邊界與冪等回歸。

### 修正紀錄 - 2026-10-09

- 閱讀順序只排除 manifest 明確標示 `properties="nav"` 的正式導覽文件，不再憑 `nav.html`／`nav.xhtml` 檔名刪除舊目錄或正文頁；空 spine 重建沿用相同安全判斷，補正式與非正式導覽回歸。

- 清除有效 JSON 且所有網址均為空的 `calibre:author_link_map` 私有快取，避免舊簡體作者鍵名殘留；保留正式作者、非空網址、未知 JSON 與自訂書目。補 property／name 型式、安全邊界及冪等測試。

- 精確清理 PDF 轉檔 XHTML head 中完整「下載器購買請聯繫作者 QQxxxxxx 或者微信xxxxxxx」占位廣告；僅替換污染 title、刪除污染 meta，正文、圖片、正常作者及其他 metadata 不變。補正簡文字、正文保留與冪等回歸。

### 修正紀錄 - 2026-10-08

- 精確移除「（Free書分享更多搜雅書）」來源導流；支援正簡字與 PDF 轉檔拆成相鄰兩段的完整括號，保留圖片說明正文、引號內引用及未完整匹配的片段，補冪等與安全邊界回歸。
- 另補已核實「（更d書f享搜索雅書.YabooK）」完整混淆字導流括號；一般站名提及與引號內引用不移除，補正簡字及正文保留回歸。

- 完整星號包裹的輕小說文庫宣傳標頭涵蓋 WenKu8.com，沿用 WenKu8.cn 的精確規則；保留翻譯署名及一般正文網址引用，補雙網域安全邊界回歸。

### 修正紀錄 - 2026-10-07

- 簡轉正尊重 XHTML `translate="no"` 的元素、後代文字與可讀屬性；元素外尾文仍正常轉換。保留人工核實的字形分析及原文姓名，不以全書或所有引句自動略過；補巢狀尾文及屬性回歸。

- 可讀欄位改用 zhTranslate 由 OpenCC 字典生成的完整字形偵測，修正短段落、人名及章名／nav／NCX 未含手工清單字元時漏轉；保留已正體段落、歧義字、日文引句與資源路徑。明確要求簡轉正時，共享轉換器缺失或轉換例外改為失敗，不再靜默輸出未轉文字。補全文字欄位與失敗傳遞回歸。

### 修正紀錄 - 2026-10-06

- 補入「萧／孙／圆」明確簡體選擇，修正孤立人名、短章名與目錄漏轉；正體段落及資源路徑仍保留。擴充短文字回歸，詞彙處理仍由共享 zhTranslate 負責。

- 可讀欄位的明確簡體選擇補入「妆／赏／饭／罚／饿」，修正短書名、作者及獨立文字節點漏轉；仍使用共享 zhTranslate，保留正體、日文引用及資源路徑，新增邊界與冪等回歸。

- 論壇來源清理加入 lightnovel.fun／app／life 網址及已核對的輕書架聯合免責、跨換行合併宣告、SF／輕小說文庫轉載句；仍限定有來源網址的頁面與完整句型，保留作者、譯者、後記、正文引用及尾端文字。補安全邊界與冪等回歸測試。

### 修正紀錄 - 2026-10-04

- 可讀欄位的明確簡體選擇補入「业／报」，修正出版社與註腳短詞漏轉；仍只把命中欄位交給 zhTranslate，已正體正文、日文及資源路徑不重轉。補混合註腳、正體／日文保存及冪等回歸。

- 缺資源引用修復涵蓋 XHTML 的內嵌 `style` 與行內樣式，沿用外部 CSS 的同類型資源比對，依文件位置修正相對路徑；確實不存在的裝飾圖 URL 改為 `none`，保留正文、現有圖片與遠端 URL。補相對路徑、正文保存及冪等回歸。

- 舊目錄連結清理保留指向實際 spine XHTML 的有效連結與章內錨點；僅去除不合法、缺頁或正式 nav 的導覽回圈，保留文字。避免一律剝除舊目錄使有效章節導航消失，補目標／錨點保存及冪等回歸。

- 缺資源模糊比對只接受同一資源類型：XHTML 不再誤指向同名 CSS，CSS 也不借用圖片或正文。仍支援 HTML／XHTML、JPEG／JPG 與資料夾差異；無真實正文目標時保留連結文字，不假造缺頁。補類型邊界及冪等回歸。

- 清除已核對的行行／QQ 2338856113／d716-716／ireadweek 完整導流段落；整頁宣傳需同時匹配核准全文指紋及 QR 圖片雜湊，保留正文、署名、不同圖片、共用資源及封面，同步 manifest／spine／目錄。新增安全邊界與冪等測試。

- 新增人工確認的 V 信 1107308023 完整括號導流標記清理，只移除獨立或正文尾端的精確標記，保留前後文字、子元素、尾端文字、署名、引號內引用與不同群號；補正簡、安全邊界與冪等測試。

- 僅清除完整星號包裹的 WenKu8 輕小說文庫網站標頭，保留普通提及及正文引用；新增回歸測試。

- 清除已逐段確認的叉叉電子書 xxdzs2 完整下載宣傳及奇書網完整製作免責句；新增三種精確星號／括號奇書網嵌入標記，接回被拆開的正文。僅匹配獨立完整句或完整標記，保留普通網址提及、引用、正文及署名，補安全與冪等測試。

- 純圖片宣傳清理略過 OPF manifest 的 XML 註解節點，保留註解，不再把其空屬性當成字串處理而中止；補上原樣保留回歸測試。

- 加入已人工確認的 Kmoe／Koobone 宣傳 PNG 雜湊清理，僅移除純圖片、無正文的宣傳頁及不再引用的廣告資源，同步 OPF、spine 與目錄；保留封面、共用圖片、CSS 引用及一般同名圖片。新增安全邊界與冪等測試。

- 將 XHTML 命名空間內的 Pubu 私有 `<ploc>` 位置標記改為合法 `<span>`，保留文字、子元素、尾端文字及有效錨點；其他命名空間不動。新增保存與冪等回歸測試，避免 EPUBCheck RSC-005。
- 移除已確認的完整網路下載免責句、指定 QQ／ireadweek 免費書導流、付費掃碼插入句及「鞋狗」App 推廣句。限定整段精確句型，不刪除作者／譯者署名、課程教材 QR 提示或正文提及；新增回歸測試。

- 保留含假名的〈〉、書名號及括號日文引用，含內層『』的書誌標題亦不轉換；仍以 zhTranslate 處理句外的簡體中文。補混合書誌回歸測試。

### 修正紀錄 - 2026-10-03

- 可讀文字簡轉正只選含明確簡體字的 XML 文字／可讀屬性，保留已為正體的欄位及含假名的日文引句；詞彙與標點仍由 zhTranslate 唯一處理，補混合內容回歸測試。

- 擴充已確認來源宣傳清理：tsdm 網址與聯合免責、yidm 精確六條下載宣告、xuanshu 推薦句及 qinkan 格式下載頁尾。維持完整句型與來源範圍限制，保留人名署名、正文、後記與一般引用；補回歸測試。

### 修正紀錄 - 2026-10-01

- ZIP 解壓前為 Windows 不安全檔名及大小寫碰撞分配唯一安全名稱，逐項保留資源並同步相對／百分比編碼的 OPF、NCX、XHTML 與 CSS 引用，避免 `extractall` 清理 `*`、`:` 後覆蓋不同章節。拒絕重複 ZIP 成員、路徑穿越與尚未支援的不安全目錄，不以資料遺失換取通過。加入資源保存與引用回歸測試。

- XHTML head 出現重複 `<title>` 時保留首個非空標題，全部為空時才用文件名補上；移除多餘空標題，避免 EPUBCheck `RSC-005`。正文與有效標題不改動，加入回歸與冪等測試。

- 僅在含 lightnovel.cn／sosg.net 的來源署名頁清除完整論壇網址、下載免責與轉載宣傳段落；保留作者、譯者、錄入署名及正文後記，加入回歸測試。
- 移除 677txt 的完整下載推薦句及緊鄰的「每天更新，喜歡的去看看」宣傳句；支援繁簡，保留其他網站引用、作者及正文，加入回歸測試。

## 1.6 - 2026-09-30

- OPF manifest 清理會移除 0 位元組 XHTML、對應 spine 項目與失效 nav 連結，避免 EPUBCheck `RSC-016`；加入回歸測試。

## 1.5 - 2026-09-25

- XHTML 正規化會移除舊轉檔器加在圖片上的私有 `active="true"` 屬性，保留圖片資源與其他合法屬性，避免 EPUBCheck `RSC-005`；加入回歸測試。

## 1.4 - 2026-09-25

- 新增 `python -m epub3itizer.kindle --keep-vertical` 選用模式，為含
  `spine page-progression-direction="rtl"` 的 EPUB3 產生 Send-to-Kindle 直排測試副本。
  此模式只移除 RTL 宣告；保留直排 CSS、固定頁／跨頁屬性、SVG、viewport、圖片與正文，
  不覆寫原書或納入一般修復。加入 ZIP、文字、圖片、直排、固定頁、跨頁與 SVG 的回歸測試。

## 2026-09-07

- 沿用既有來源廣告清理，新增 ePUBw 完整下載宣傳句的繁簡比對，保留周圍正文及一般網站名引用；加入跨行內標籤、繁簡與段落尾文回歸測試。

## 1.3 - 2026-09-23

- XHTML 正規化現在會將樣式表 `<link>` 錯寫的 `src` 屬性移至標準 `href`。保留原本路徑並避免 EPUBCheck `RSC-005` 對 `<link src="...">` 的屬性錯誤；加入回歸測試。

- XHTML 正規化會移除已棄用的 ARIA `role="doc-*"` 註腳角色，保留 `epub:type` 與其他 ARIA 角色，避免 EPUBCheck `RSC-017` 的 `doc-endnote`／`doc-endnotes`／`doc-backlink` 警告；加入回歸測試。

- XHTML 正文中的舊式 `<image>` 元素改為標準 `<img>`；SVG 命名空間內的圖像元素不動。另依實際檔頭將 JPEG／PNG／GIF／WebP／TIFF 圖像更正為相符副檔名並回寫引用，避免 EPUBCheck `RSC-005` 與 `PKG-022`；加入回歸測試。

- SVG 圖像式目錄的 `<a xlink:href>` 現在會套用遺失 XHTML 連結修復。遇到
  `xhtml/xhtml/p-005.xhtml` 這類重複資料夾路徑時，會依實際檔案回寫為
  `p-005.xhtml`，避免 EPUBCheck `RSC-007`；加入回歸測試。

- 修正內容實為 PDF、但副檔名與 manifest 類型誤標為 CSS 時被當作 UTF-8 樣式表解碼而中止的問題；改由檔頭辨識為 PDF、修正 media type，並保留原始二進位內容。

- 修正 EPUB2 OPF 中無前導空白的 XML 註解被誤判為未閉合元素，造成 manifest／spine 錯誤落入 metadata 的問題；加入結構回歸測試。

- 修正把 `a`、`ins`、`del` 一律視為行內容器的判斷，改為繼承外層內容模型。
  保留合法區塊連結中的段落及分隔線，避免《綠猴劫》目錄的段落被改為 `span` 而併行。
  加入合法、巢狀透明容器與受行內限制案例的回歸測試；參考 calibre 的 HTML5
  解析策略及 HTML 標準，不移植第三方程式碼。

- 新增選用的 `python -m epub3itizer.kindle`，為 EPUB3 文字書另外製作橫排流式
  Kindle 副本。統一閱讀方向、移除混合固定頁面設定，將無裁切的單圖 SVG
  包裝改為等比例圖片，並可明確指定內容語言。保留原書，普通修復不自動套用。
  絕對定位、全書固定版面或複雜 SVG 會停止，避免破壞圖文內容。
  EPUBCheck 通過不代表 Amazon 雲端一定啟用流式排版，仍須重新傳送確認。

- OPF 同時將多張圖片標成 `cover-image` 時，若既有 `meta name="cover"`
  唯一指向其中一張，移除其他圖片的封面標記，保留圖片與其他屬性。
  無明確指定或指定互相衝突時不猜測。參考 calibre 封面唯一屬性的處理思路，未移植程式碼。

- XHTML 清理新增移除 AZW3/Calibre 轉檔後掉入正文的孤兒 HTML 屬性殘片，
  例如 `id="_idParaDest..." class="..." aid="..."&gt;` 或
  `d="footnote-..." class="_idFootnote" ...&gt;`。這類殘片可能不會讓
  EPUBCheck 失敗，但會在閱讀器正文中顯示錯誤文字。
- XHTML 清理新增移除 Calibre/AZW3 來源殘留的 `aid` 私有屬性，避免章名段落
  等元素通過前段修復後仍被 EPUBCheck 回報屬性不合法。
- XHTML 清理新增移除與元素同名、或空值且名稱像 HTML 標籤名的非法屬性，
  例如 Calibre 轉檔偶發產生的 `<div div="">`、`<div i="">`，避免
  EPUBCheck 回報該屬性不允許使用。

## 1.2 - 2026-09-03

- OPF 清理新增正規化 `<package xml:lang>` 的修復；若 package 層殘留
  `xml:lang="z"` 等不合法語言碼，會依 metadata 語言改為合法值，避免
  EPUBCheck `OPF-092`。
- OPF manifest 清理新增移除指向不存在 manifest id 的 `fallback` 屬性，避免
  EPUBCheck `OPF-040`。
- XHTML 清理新增同一 `head` 只保留一個 `meta charset` 的修復；若舊檔同時有
  `<meta charset="...">` 與 `Content-Type ... charset=...`，會保留單一
  UTF-8 宣告，避免 EPUBCheck 回報同一文件有多個 charset meta。
- 前置檔名空白修復與路徑大小寫修復遇到不可讀的舊 NCX 或其他文字檔時會跳過
  內容改寫，讓後續 manifest/NCX 清理規則接手移除或修復，避免亂碼 NCX 在修復
  流程初期就中止。

## 1.1 - 2026-08-29

- XHTML 清理新增移除 `kmoetag` 私有屬性，避免 Kobo/商店來源殘留屬性造成
  EPUBCheck 回報 XHTML 屬性不合法。
- XHTML 與 OPF spine 清理擴充 KMOE 私有欄位處理，會移除 `kimageraw` 與
  `kmoe-*` 類屬性，例如 `kmoe-pagedirect`，避免漫畫 EPUB 的私有閱讀器標記
  造成 EPUBCheck 失敗。
- OPF manifest 清理新增移除空白或檔頭無效的 raster 圖片資源，若只剩空檔或
  非圖片內容會同步移除 manifest 項目與殘留檔案，避免 EPUBCheck
  `MED-004` / `PKG-021`。
- OPF metadata 清理新增移除空白的 Dublin Core 選填欄位，例如
  `dc:source`、`dc:relation`、`dc:coverage`、`dc:rights`，避免 EPUBCheck
  回報 metadata 文字內容長度不足。
- XHTML 正規化新增修復：當樣式表 `<link rel="stylesheet">` 的 `type`
  被舊製作工具誤寫為檔案路徑等非 MIME 值時，自動改為標準 `text/css`，避免
  EPUBCheck 回報 stylesheet `type` 屬性不合法。
- fixed-layout XHTML 修復新增 SVG 封面尺寸推論：若 spine itemref 宣告
  `rendition:layout-pre-paginated`，但封面頁只用 `<svg viewBox="...">`
  而沒有 `<img>`，會自動補上合法 `viewport` meta，避免 EPUBCheck 回報
  fixed layout 文件缺少 viewport。

## 1.0 - 2026-08-21

- 文字檔讀取新增 XML encoding 宣告偵測與 `cp950` / `big5` /
  `gb18030` fallback；遇到舊書 XHTML/OPF 不是 UTF-8 時，修復流程會先正確
  讀入，再由輸出流程統一寫回 UTF-8，避免非 UTF-8 原始檔中止轉換。
- OPF metadata 清理新增移除 `<meta>` 上 EPUB3 不允許的私有屬性，例如
  `lic`、`ver`、`url`；同時移除只有 `name` 但缺少 `content` 的 OPF
  `<meta>`，避免 EPUBCheck 回報 OPF metadata 屬性不合法或缺必要
  `content`。
- 官方 nav 清理新增移除 `nav` 裡沒有可讀內容的空 `<div>`，包含常見的
  `style="display: none"` 殘留節點，避免 EPUBCheck 回報 nav 結構中不允許
  `div`。
- OPF manifest 清理新增移除已被 XHTML 正規化後不再需要的 stale `scripted`
  property；當 JavaScript 已由清理流程移除時，會同步清掉 manifest
  `properties="scripted"`，避免 EPUBCheck 回報 scripted 不應宣告。
- 固定版面 viewport 修復新增移除 stale 全域
  `rendition:layout=pre-paginated`：當一般文字頁無法從圖片推得 viewport
  尺寸時，會移除錯誤的全書固定版面宣告，避免 EPUBCheck `HTM-046`。
- 官方 nav 清理新增移除沒有可讀文字的空 `<span>` 與 `<a>`，避免 Google
  Books / Kobo 殘留錨點造成 EPUBCheck 回報 nav span/anchor 內容為空或
  結構不合法。
- 官方 nav 清理新增將 `nav` 內殘留的 `<ul>` / `<menu>` 轉成 EPUB3 合法
  `<ol>`，保留原本目錄項目與層級，避免 EPUBCheck 回報 toc 裡不允許
  unordered list。
- 缺失 XHTML 資源修復流程新增空檔/不可解析檔案防護；掃描連結與快取
  anchor id 時若頁面解析不到 root，會跳過該檔而不是中止整本修復，避免
  圖像型或殘缺頁面造成 `NoneType.iter`。
- OPF manifest 清理、超連結目標掃描與固定版面 viewport 修復也會跳過空檔或
  不可解析 XHTML，避免漫畫/圖像型 EPUB 的空殼頁造成 `NoneType.xpath`。
- `repair-only` 新增把純文字 `.html/.xhtml` 包成最小合法 XHTML、缺少 EPUB3
  nav manifest 時自動補 `nav.xhtml`、缺少 `dcterms:modified` 時補合法時間，
  並移除未宣告 prefix 的 OPF metadata property，例如 `ebpaj:guide-version`，
  避免固定版面/漫畫 EPUB 因舊閱讀器私有欄位而無法通過 EPUBCheck。
- XHTML 與 OPF 清理新增處理掃描/OCR 破碎文字被誤解析成大量空屬性標籤、
  正文標題反向連回非 spine `nav.xhtml`、圖片被放入 spine、以及 nav 連到圖片
  而非正文頁的情況；修復時會保留可讀文字、移除違規連結，並讓 nav 回到第一個
  合法正文 XHTML。
- XHTML entity 清理新增修復缺少分號的已知 HTML entity，例如
  `&quot"` 會在解析前轉為安全數字 entity，避免網頁快照轉出的 EPUB 因
  屬性值內半壞 entity 造成 EPUBCheck `RSC-016` 致命錯誤。
- CSS sanitizer 新增移除 `text-spacing-trim: trim-start;`，包含一般 CSS
  規則與 XHTML inline style，避免新式/未廣泛支援的間距修剪宣告造成
  EPUBCheck 或閱讀器相容性問題。

## 2026-08-11

- CSS 參照修復新增清理失效 `@import` 規則；當 CSS 匯入的檔案不存在且找不到
  可安全重連的同名資源時，會移除該 `@import`，避免 EPUBCheck 回報缺少被
  引用資源。

## 2026-08-07

- OPF 清理新增移除 EPUB3 spine 上不合法的 `page-map` 屬性，避免固定版面或
  直排書從舊工具轉出後觸發 EPUBCheck `RSC-005`。
- OPF manifest 清理新增移除已被 XHTML 正規化後不再需要的 stale `switch`
  property，避免 EPUBCheck 回報 `switch` 屬性沒有在內容文件中宣告。
- CSS sanitizer 新增移除規則結尾後的中文註記，例如 `}（加標識"I"）`，避免
  EPUBCheck 將註記文字解析成不合法 CSS token。

## 2026-08-05

- OPF/package 清理新增移除未登記且未使用的巢狀重複封面檔，例如
  `OEBPS/OEBPS/cover.jpg`；若同層已有正式 `OEBPS/cover.jpg`，會避免把殘留
  孤兒圖重新加入 manifest。
- 固定版面 viewport 修復會同時辨識 spine itemref 上的
  `rendition:layout-pre-paginated`；若頁面缺少 viewport，會從第一張本地圖片
  的實際尺寸補上 `<meta name="viewport" ...>`，避免 EPUBCheck `HTM-046`。
- `repair-only` XHTML 清理會把非 table 位置的 `<caption>` 改為合法的
  `<figcaption>` 或 `<div>`，避免圖片 `<figure>` 裡的舊式 caption 觸發
  EPUBCheck `RSC-005`。
- OPF 清理會移除 manifest/itemref `properties` 裡不是 XML NMTOKEN 的殘留
  token，例如 `viewport-width=1514, height=2048`，避免 EPUBCheck
  `RSC-005` / `OPF-027`。
- 官方 toc nav 清理會依 spine 閱讀順序重排同層目錄項，避免目錄連結倒退時
  觸發 EPUBCheck `NAV-011`。
- OPF metadata 清理會把非法的 `urn:uuid:*` 識別碼替換成合法 UUID，避免
  EPUBCheck `OPF-085`。

## 2026-08-03

- `repair-only` OPF spine 清理新增處理 EPUBCheck `OPF-096`：若 XHTML
  spine item 被標成 `linear="no"`，但整本書沒有任何超連結可到達該檔案，
  會移除 `linear` 讓它回到主線閱讀；若正文或目錄仍有連結可達，則保留
  非線性設定。
- `repair-only` OPF manifest 清理新增 XHTML 內容特徵偵測：若 XHTML 檔案內含
  SVG 或 MathML，會自動補上對應的 `properties="svg"` / `properties="mathml"`；
  若修復後已不含 SVG 或 MathML，也會移除 stale property，避免 EPUBCheck
  回報屬性缺少或不應宣告。

## 2026-08-01

- OPF 清理新增 metadata/manifest XML id 衝突修復：manifest 與 spine 使用中的資源 id 會優先保留，metadata 中撞名的 `id` 會改為 `meta-...`，並同步 metadata 內 `refines`，避免 EPUBCheck 回報 `Duplicate "title"` 等錯誤。

## 2026-07-26

- 官方 nav 的 `NAV-011` 修復更正父層目錄判斷：若父層連結目標晚於子項目中的最早 spine 位置，會把父層連結降級為純文字，保留子章節連結，避免 Send to Kindle 或 EPUBCheck 因目錄閱讀順序倒退而拒絕或警告。
- 簡轉正 `--convert-chinese s2tw` 改為優先使用 `D:\github\zhTranslate` 共用文字轉換層，避免 `epub223`、`metaFinder` 各自維護重複自訂詞表；EPUB 結構安全仍由 `epub223` 控制，只轉換可讀文字與允許的文字屬性。
- 官方 nav 修復新增處理只有一般 `<div><ul>` 目錄、卻在 OPF manifest 標為 `properties="nav"` 的 EPUB3 檔案；修復時會補成唯一的 `<nav epub:type="toc">` 並把 `ul/menu` 轉為 `ol`，避免 EPUBCheck 回報 `Exactly one "toc" nav element must be present`。
- CSS sanitizer 新增移除多看私有 `duokan-text-indent` 宣告，包含一般 CSS 規則與 XHTML inline style，避免 `duokan-text-indent: 0;` 殘留到 EPUB3。
- CSS sanitizer 新增修復方向屬性中把連字號誤寫成空格的情況，例如 `padding top:`、`padding bottom:` 會轉為 EPUBCheck 可解析的 `padding-top:`、`padding-bottom:`。
- XHTML 清理新增移除 `言情兔` / `yanqingtu.com` 的來源廣告短段；規則需同時命中站台識別與下載、購買正版或更多精彩等廣告語，避免只因正文提到一般宣傳詞而誤刪。
- XHTML 清理新增移除 `請看小說網` / `qinkan.net` 的來源廣告，包含短段落宣傳與正文中夾入的 `[www.qinkan.net請看小說網]`、`[請看小說網·電子書下載樂園—wＷw.QiＳuu.cＯm］` 類浮水印；段落刪除規則需同時命中「更多精彩 / 更多好書」與站台識別，避免誤刪一般正文。
- TOC 修復新增處理製作器誤產生的目錄頁：會把大量空 `<dd/>` 的 `<dl><dt><a>章節</a></dt><dd/>` 目錄轉成正常 `<ol><li>`，也會將 `chapter0001 -> chapter0002 -> chapter0003` 這種錯誤單鏈巢狀 nav 攤平成同層章節清單，避免目錄前幾章被降級成不可點擊文字或顯示成不合理階層。

## 2026-07-25

- CSS sanitizer 新增移除 `text-combine: horizontal;`，與既有 `text-combine-horizontal: all;` 清理規則一併避免直排舊式合字宣告造成 EPUBCheck 或閱讀器相容性問題。
- CSS sanitizer 新增清理重複 CSS 屬性宣告，包含 XHTML inline style 與一般 CSS 規則區塊；同名屬性依 CSS cascade 保留最後一次宣告，避免 Sigil 檢查書本回報 `Unexpected duplicate`。

## 2026-07-24

- OPF metadata 清理會將既有 `dc:language` 的底線語言碼正規化為合法 BCP 47 格式，例如 `zh_TW` 會改成 `zh-TW`，避免 EPUB2 轉 EPUB3 後觸發 EPUBCheck `OPF-092`。

## 2026-07-18

- 簡轉正 `--convert-chinese s2tw` 參考 `Hopkins1/TradSimpChinese` 的 quotation marks 做法，新增西式彎引號 `“”‘’` 到臺灣正體直角引號 `「」『』` 的直接對照轉換；仍只處理可讀文字與文字屬性，不改 `href`、`src`、`id`、CSS、URL 或 script/style 內容。
- 官方 `nav.xhtml` 清理新增 `NAV-011` 閱讀順序修復：當父層 `<li>` 同時含有子目錄，且父層連結目標位於子項目前方或相同 spine 項目時，會把父層 `<a>` 改為 `<span>`；同一 spine 檔案若已出現 fragment 連結，後續裸連結會降級並由既有空 leaf 清理移除，避免目錄連回檔案開頭造成順序倒退。
- EPUB 清理新增移除 `Provider.txt`，不論其位於 EPUB 包內哪個資料夾，都會一併清除實體檔、OPF manifest 項目與 spine 參照，避免平台殘留檔被保留在書內。

## 2026-07-17

- OPF metadata 清理新增移除私有 `<meta property="hdf">`，避免部分 EPUB 內殘留 HyRead/DRM 相關私有 metadata 時觸發 EPUBCheck `OPF-027`。
- CSS sanitizer 新增移除 `text-combine-horizontal: all;`，避免舊排版或閱讀器私有樣式造成 EPUBCheck / 閱讀器相容性問題；既有 `calibre_bookmarks.txt` 實體檔與 manifest 項目清理規則維持啟用。

## 2026-07-13

- 抽離可重用的 EPUB 修復流程到獨立模組 `epub3itizer.repair`，讓單獨修復與 EPUB2 -> EPUB3 轉換後的後處理共用同一套規則。
- CLI 新增 `--repair-only`，可直接對單一 EPUB 或整個資料夾套用修復流程，不必先做 EPUB2 -> EPUB3 轉換。
- 轉 EPUB3 的主流程改為呼叫共用修復管線，避免轉檔與修復邏輯分叉。

## 2026-07-13

- 補強 agent 慣例：任何需要 Codex 介入的 EPUB 修復，必須先分類為可泛用修復、單本書特有破損、不安全泛化或需要人工內容判斷。
- 明確規定可泛用修復不得只停留在單本 EPUB 或工作檔，必須寫回 `epub3itizer`、補 regression test、更新 README 或相關說明、更新 `CHANGELOG.md`，並執行 `pytest -q` 後再回到書庫流程重跑。
- 新增可選簡轉正參數 `--convert-chinese s2tw`，沿用 `metaFinder` 的 `OpenCC("s2tw")` 與自訂替換檔做法；預設仍為 `none`，不會自動改動書內文字。
- 簡轉正會處理 XHTML、OPF、NCX、XML 的可讀文字與 `title`、`alt`、`content` 等文字屬性，並避開 `href`、`src`、`id`、CSS、URL 與 script/style 內容。
- 自訂替換會在 OpenCC 轉換前後各套用一次，讓簡體 key 與正體 key 都能命中，例如 `实时` 可正確轉為 `即時`。
- 新增回歸測試，覆蓋簡轉正 CLI 參數、OpenCC 與自訂替換、以及不改連結路徑的行為。

## 2026-07-12

- 修正 OPF package `prefix` 漏宣告 `calibre:` 的問題；當 manifest item 使用 `calibre:title-page` 等屬性時，轉換器會自動補上 `calibre: http://calibre.kovidgoyal.net/2009/metadata`，避免 EPUBCheck `OPF-028`。
- 同步讓轉換器在需要時宣告 `media: http://www.idpf.org/epub/vocab/overlays/#`，避免後續 Media Overlays metadata 產生同類 prefix 錯誤。
- 新增回歸測試，覆蓋 `calibre:title-page` 的 package prefix 輸出。
- CLI 啟動時會將 stdout / stderr 切到 UTF-8，避免路徑含變音符號或其他 Unicode 字元時，最後一行 `Output written to ...` 因 `cp950` 編碼失敗而誤報。

## 2026-07-11

- 強化剩餘 EPUB2 轉 EPUB3 的 EPUBCheck 修復：
  - inline `style` 會移除 `file:///`、`res:/`、遠端 `http(s)://` 的 `url(...)` 宣告，避免 Sigil 暫存路徑或遠端資源造成 `RSC-030` / `remote-resources` 錯誤。
  - CSS 會移除破損的 `@namespace` 單行宣告，例如只剩 `@namespace h "http:` 的半截字串。
  - XHTML 表格中直屬 `<col>` 會自動包進 `<colgroup>`；若 `table` 直屬內容已混入 `div` 等壞結構，會保守降級成一般 `div`。
  - 會移除 `times` / `new` / `roman` / `serif` / `tooltip` 等由字型或網站工具誤拆出的非法 XHTML 屬性。
  - 會移除 Vue/Docsify 類網頁匯出殘留的 `v-*` 屬性，以及 EPUB XHTML 不接受的 `download` 屬性。
  - `colspan` / `rowspan` 只保留在 `td` / `th`，若誤出現在 `span` 等元素上會移除。
  - OPF metadata 會移除 EPUBMerge/Calibre 合集常見的空 `meta refines`、空 `belongs-to-collection`、指到不存在目標的 `#series` refine，並修復空或格式不合法的 `dcterms:modified`。
  - CSS 會移除被截斷的 `data:` URL 宣告，例如未閉合的 `background-image: url("data:image/...`。
- 強化第四批 500 本轉換的 EPUBCheck 修復：
  - 舊 XHTML 標籤 `<tt>` 會改為 `span`，`title_...` 這類轉檔殘留自訂標籤會改為 `div`。
  - 孤立的表格結構元素如 `tr` / `td` / `th` 若不在合法表格父層中，會降級成一般 `div` 或 `span`，避免目錄頁把 table row 直接塞進 span 時驗證失敗。
  - 畸形 ruby 若在 `rt` 後直接夾入正文而不是合法 `rp`，會扁平化為一般文字，保留正文並移除 `rt` / `rp`。
  - 會移除 `blockquote` / `q` 等元素上的舊式 `cite` 屬性，避免 `cite="輸入url"` 被當成缺失資源。
  - 會移除誤寫在 XHTML 元素上的 `body` 屬性，例如 `<blockquote body="">`。
  - OCR 或舊轉檔殘留的假標籤 `<order>` / `<do>` / `<mi>` / `<so>` 會改為 `span`，`<a___>` / `<b___>` 這類字母加底線的假標籤也會改為 `span`。
  - 由假標籤轉為標準標籤時，會移除 `of=""` / `the=""` / `zenith=""` 這類由文字碎片誤解析而來的非法屬性。
  - CSS 會將全形冒號 `：` 正規化為半形 `:`，修復 inline style 中常見的中文輸入法污染。
  - 空白或不含 `<svg>` 的 SVG 檔會從 OPF manifest 移除並刪除，後續引用修復會移除失效圖片引用。
  - `cover_page.xhtml` 若被標成 `linear="no"`，會改回主線閱讀，避免 EPUBCheck 回報 non-linear cover 不可達。
- 強化第三批 500 本轉換的 EPUBCheck 修復：
  - CSS 會移除舊工具留下的 `//` 單行註解、修復 `font-family` 中間誤寫的分號，並移除任意位置多出的孤立右大括號。
  - CSS 若 `//` 註解尾端夾帶右大括號，會保留該括號；若移除註解後下一個 selector 誤落在未閉合區塊內，會補回區塊閉合。
  - CSS 會修復 `color-#b49c84;` 這類把冒號誤寫成連字號的顏色宣告。
  - XHTML 會移除空表單控制項，例如閱讀器 CFI 用的 `<form><input type="hidden">`，避免 EPUBCheck 要求 `scripted` property。
  - XHTML 會將非標準 `<debagame>` 改為 `div`，移除壞掉的 `a=""` 屬性，並把 heading/inline 內容中的 `<hr>` 降級成可驗證的 `span` 分隔線。
  - XHTML 會移除舊式 table `summary` 屬性，避免 EPUB3 XHTML 屬性驗證失敗。
  - XHTML 解析前會逃逸正文中形似 XML 的中文假標籤，例如 `<我在明末有套房/>`，避免被當成非法元素。
  - OPF 清理會移除 EPUB3 不允許的舊式 `dc:*` 屬性與 `meta scheme`，例如 `dc:identifier scheme`、`dc:contributor role`。
  - OPF 清理會移除多看私有 `duokan-page-fitwindow` / `duokan-page-fullscreen`，不論它出現在 manifest item、itemref 屬性或 properties token。
  - 若舊 OPF 把 `spine` 誤放在 `manifest` 內，或轉換後 spine 空掉，會移回正確位置並依 XHTML manifest 補出主閱讀順序。
  - 官方 `nav.xhtml` 會依最終 OPF spine 再清一次，連到非 spine XHTML 的項目會降級為純文字，並移除空的 `ol`。
  - 官方 `nav.xhtml` 若 TOC 被過濾到沒有任何 `li`，會用第一個 spine 項目補 fallback；空的 landmarks nav 會移除。
  - 轉換流程收尾會在最後一次 OPF manifest/spine 清理後，再跑一次官方 nav 清理，確保 nav 使用最終 spine 狀態。
  - 轉換流程收尾會重新清理所有 CSS，涵蓋後段才補進 manifest 的 CSS 檔，避免殘留 `res:///` 或 `file:///` 裝置字型引用。
- 強化本批 EPUB2 轉 EPUB3 的 EPUBCheck 修復：
  - NCX 解析會跳過註解與 processing instruction 等非元素節點，避免舊書目錄檔造成轉換中斷。
  - 固定版型 `pre-paginated` XHTML 若缺 viewport，會依頁面第一張圖片尺寸補上 `meta name="viewport"`。
  - CSS 會移除 EPUBCheck 不允許的 `direction` 屬性，並正規化舊 IE 星號 hack，例如 `*font-size`。
  - CSS 會將誤寫的全形百分號 `％` 正規化為半形 `%`，避免尺寸值被 EPUBCheck / 閱讀器解析失敗。
  - OPF spine 中 cover/titlepage XHTML 若被標成 `linear="no"`，會改回預設主線閱讀，避免 non-linear content 不可達。
- 強化後續 500 本批次轉換的 EPUBCheck 修復：
  - 將舊式 `switch` / `case` / `default` 與 namespaced `epub:switch` / `epub:case` / `epub:default` 扁平化為一般 XHTML `div`，避免缺 `required-namespace` 或元素不合法。
  - 清理 iframe/audio 等舊工具輸出的私有屬性，例如 `marginwidth`、`frameborder`、`activestate`、不適用的 `placeholder`。
  - 同步 XHTML 根節點的 `lang` 與 `xml:lang`，避免兩者值不一致。
  - 將 `pre` 內不合法的 block 標題元素轉為 inline，避免 EPUBCheck 結構錯誤。
  - XHTML 內嵌 `<style>` 也會套用 CSS sanitizer，移除遠端或裝置字型引用。
  - CSS 會修復孤立 `!important`、多餘分號與破損註解造成的孤立宣告區塊。
  - BMP 轉 PNG 會偵測實際檔案內容，不只依副檔名；副檔名偽裝為 `.jpg` 的 BMP 也會轉換並改寫引用。
  - 移除不支援的 EMF/WMF 圖片引用與 manifest 項目，避免 foreign resource 缺 fallback。
  - OPF spine 中指向 `nav.xhtml` 的 itemref 會移除，即使 idref 不是 `nav`，避免 non-linear nav 不可達。
  - 無 namespace 的 HTML 文件會提升為 XHTML 預設 namespace，避免 EPUBCheck 回報空 namespace 元素不合法。
  - 遠端 iframe 廣告引用會移除，避免 remote resource 需要 OPF 宣告。
  - 孤立或缺少 `src` 的 `source` 元素會移除，避免 audio/video 外層結構不合法。
  - 修復 recover parser 後 `<meta>` 誤包住 `<link>` / `<title>` 的 head 結構，並將 head 中誤轉成 `span` 的標題還原為 `title`。
  - HTML 文件若缺少 `body`，會自動補上空 `body`，避免只有 head/title 的短頁面無法通過 EPUBCheck。
- 強化第二批 500 本轉換的 EPUBCheck 修復：
  - 空 `id` 屬性會移除，避免 `id=""` 不符合 XML token 規則。
  - `lang` / `xml:lang` 會正規化異體破折號，空或不合法語言碼會回補 `zh-Hant`。
  - 非標準 inline 標籤 `<r>` 會改為 `span`，誤入 XHTML 內容的 `<spine>` 會改為 `div`。
  - 壞掉的屬性名 `clasＶs` 會在解析前修正為 `class`。
  - 畸形 ruby 若含空 `rt`，會保守扁平化並保留可讀文字，避免 EPUBCheck 要求 `rp` 位置時失敗。
  - 移除事件處理屬性，例如 `oncontextmenu`，避免輸出 EPUB 需要 `scripted` property。
  - CSS 會移除孤立右大括號，並在缺少右大括號時自動補齊。
  - 空 NCX 會視為沒有 TOC，不再讓轉換流程因 `NoneType` 中斷。
  - 從 OPF `spine` 誤入 XHTML 的屬性如 `page-progression-direction`、`toc` 會移除。
  - `@font-face` 清理後若殘留孤立右大括號，會一併移除。
- 修正 CSS 檔案開頭殘留孤立宣告區塊，例如 selector 被清掉後剩下
  `font-weight: bold; }`，避免 EPUBCheck `CSS-008`。
- 清理 XHTML `head` 中誤放的 block 元素，例如頁面分隔用 `div`，避免
  EPUBCheck 判定 `head` 結構不合法。
- 清理空的 OPF `meta property="role"`，避免 refines 角色 metadata 沒有
  內容時造成 EPUBCheck 失敗。
- 強化 CSS 修復：移除註解後多餘分號、將 `width=100%` 這類誤寫轉成
  `width: 100%`、移除空宣告如 `font-family: ;`，並把遠端 `url(http...)`
  改成 `none`。
- 若環境有 Pillow，會將 EPUB 內的 BMP 圖片轉成同名 PNG 並改寫引用，
  避免 EPUB3 foreign resource 缺 fallback 的錯誤。
- 清理 OPF 中空的 `ibooks:*` meta，例如 `ibooks:version` 與
  `ibooks:specified-fonts`，避免未宣告 prefix 與空內容造成 EPUBCheck
  失敗。
- 修正 CSS 宣告尾端殘留反斜線，例如
  `border-bottom: ...;\`，避免 EPUBCheck `CSS-008`。
- 修正末端 XHTML 正規化誤刪官方 nav `epub:type="toc"` 的問題；現在只會移除
  無 namespace 的舊式 `type` 屬性，保留 EPUB3 nav 必要的 `epub:type`。
- 修正壞掉的 XHTML namespace，例如 `http://www.w3.org/十九99/xhtml` 這類
  OCR/轉碼污染，會正規化回標準 `http://www.w3.org/1999/xhtml`。
- 轉換流程末端新增一次全 XHTML 結構正規化，確保移除舊 TOC 連結、
  修復 nav 或其他後處理之後，仍會清掉表格內空 `span` 等 EPUBCheck
  結構錯誤。
- 放寬表格空 `span` 清理，不再要求元素帶 XHTML namespace，避免舊 HTML
  轉檔後 `<table><tr>...</tr><span/><tr>...</tr></table>` 仍被 EPUBCheck
  判為結構錯誤。
- 移除多看/掌閱圖庫常見的私有 `gallery` 屬性，保留原本 `div` 與圖片內容，
  避免 XHTML 屬性驗證失敗。
- 修正 EPUBCheck 後續發現的表格與 EPUB switch 殘留問題：移除
  `table` / `tr` 等表格結構中空的 `<span/>`，並將孤立的
  `<case>` / `<defaultcase>` 正規化為 `div`，同時移除
  `required-namespace` 屬性，避免 XHTML 結構驗證失敗。
- 強化 OPF metadata 清理：移除 `dc:builder`、`dc:builder_version` 等
  EPUB/DC 規範未定義的 metadata 元素，但保留並轉換可修復的 `dc:meta`。
- 強化 CSS 修復：清除 CSS 檔案開頭或內容中的 ASCII 控制字元，避免
  EPUBCheck `CSS-008`；CSS `url(...)` 若引用不存在的資源，會先嘗試用
  書內同名資源改寫，找不到時改為 `none`，保留其他背景設定。
- 修正 OPF manifest 去重時可能誤刪 `meta name="cover"` 指向的 cover
  item：現在同一路徑重複時會優先保留 cover metadata 或 `cover-image`
  property 指向的項目，避免封面 metadata 變成懸空引用。
- 調整轉換流程末端，在移除舊 TOC 連結與清理官方 nav 後，會再執行一次
  XHTML 引用修復、補 manifest 與 OPF 清理，確保最後打包進 EPUB 的內容
  不會保留後續流程產生或漏掉的壞連結。
- 依照目前書庫轉換失敗案例，擴充 EPUBCheck 後續修復：當 `dl` 已混入
  `div`、裸文字或其他無法安全保留語意的子層時，改採 Sigil/calibre
  式保守修復，將整個區塊扁平化為 `div`，保留文字內容但避免 EPUB3
  定義列表結構錯誤。
- 修正 XHTML 連結直接指向圖片資源造成 EPUBCheck `RSC-010` 的問題：
  轉換後會將這類 `<a href="...jpg/png">` 改為非連結 `span`，並保留原本
  的文字或內嵌圖片。
- 強化官方 `nav.xhtml` 清理：若修復流程移除失效 href 後留下只有
  `span`、沒有子 `ol` 的目錄 leaf，會自動移除該 leaf，避免 EPUB3 nav
  結構出現 `li` 缺少必要內容的錯誤。
- 修正 OPF 位於 `OEBPS/content.opf` 時，manifest href 誤寫成
  `OEBPS/cover.jpg` 的情境：現在會先轉成 package 相對路徑 `cover.jpg`
  再用解析後路徑去重，避免 EPUBCheck 誤判引用 `OEBPS/OEBPS/cover.jpg`
  未宣告。
- EPUB3 轉換後會移除舊 EPUB2 `toc.ncx` manifest 項目、實體檔與
  spine `toc` 屬性，改以產生的 `nav.xhtml` 作為標準目錄，避免舊 NCX
  殘留錯誤路徑被 EPUBCheck 驗出。
- EPUB3 OPF 清理會移除舊 `<guide>` 區塊，避免 EPUB2 guide 中的壞
  fragment 造成 EPUBCheck `RSC-012`。
- 強化 XHTML 清理：移除 `head` 直屬文字與子元素 tail 中的非 XML
  whitespace，並移除包含底線的不合法屬性名稱，例如 `text-align_`。
- 進一步擴充 EPUBCheck 失敗後的自動修復：移除全形問號形式的假 XML
  宣告，將 `html` 根節點中誤落在 `body` 後的內容搬回 `body`，清理
  `dl` 開頭不合法的 `dd`，並移除所有元素上 EPUB3 不允許的 `target`
  屬性。
- 修正 NCX 仍保留已被過濾掉的舊連結問題：轉換流程現在會在 TOC
  對照 final spine 後重新寫回 `toc.ncx`，並移除 TOC/guide 中不安全的
  fragment，避免 EPUBCheck 的缺檔與不存在錨點錯誤。
- 強化 OPF manifest 路徑清理：當 OPF 位於 `OEBPS/content.opf` 且 href
  誤寫成 `OEBPS/cover.jpg` 時，會修成以 OPF 為基準的 `cover.jpg`，
  並以解析後 package 路徑去重。
- 強化 inline style 清理：移除混進 style 的非 CSS 宣告，例如
  `class=`，並補齊缺右括號的 `url(...)`。
- 只保留一個 `meta property="dcterms:modified"`，避免 EPUBCheck 因
  EPUB3 修改時間 metadata 出現多次而失敗。
- 依照 calibre Editor「Check book」可自動修復的方向，擴充 EPUBCheck
  失敗後可重用的結構修復：清理 `head` 內誤留的裸文字、將不合法的孤立
  `li` 改為段落、將 `ul` / `ol` / `menu` 直屬非清單元素改為 `li`，並
  移除或轉換 body 內誤放的 `meta` / `style` / `title`。
- 修正缺 `href` 的 `a` 在引用修復後仍留作非法 anchor 的問題：若連結
  目標或 fragment 無法安全解析，會移除 `href` 並改成 `span`。
- 強化 OPF 清理：移除 manifest/itemref properties 中的
  `duokan-page-fullscreen`，並將只有日期文字的 `opf:meta` 轉為 EPUB3
  合法的 `meta property="dcterms:modified"`。
- 修正無 namespace XHTML fallback 會寫入非法 `xmlns:epub` 屬性的問題。
- 擴充 CSS 清理，修復舊檔中選擇器被多插入數字造成的 EPUBCheck CSS
  解析錯誤。
- 擴充 EPUBCheck 後續修復流程中發現的 XHTML 正規化：修正大寫 XHTML
  標籤、`PUBU` / `spen` 等非標準或錯字元素，移除 `base`，將無 `href`
  或巢狀的 `a` 改為 `span`，移除不合法 `name` / `cid` / `value` 屬性，
  並將 HTML5 尺寸屬性中的非整數值移到 CSS `style`。
- 修正原始檔含異常 namespace 屬性導致轉換程式失敗：解析 XML 前會
  正規化常見錯誤 namespace，例如 XHTML `https` / `/epub`、OPF
  `/v3`、DC `elements/1.0/`，並移除非法 `xmlns:xmlns` 與錯誤
  `xmlns:xml` 宣告；OPF 進入轉換器前也會套用同一套修復。
- 擴充「被引用資源未在 OPF manifest 宣告」的自動修復：除了
  `href` / `src` 與 CSS `url(...)`，也會掃描 `poster`、`data`、
  `srcset`、SVG `xlink:href` / `href` 以及 CSS `@import`，若檔案實際
  存在但未宣告，會自動補進 manifest。
- 修正 OPF metadata 缺少 EPUB 必填 `dc:title` / `dc:language` 的問題：
  若缺少或內容空白，會補入 fallback `Untitled` 與書庫慣例語言
  `zh-Hant`，避免 EPUBCheck 因必要欄位缺失失敗。
- 移除 OPF manifest `item` 上的多看閱讀私有屬性
  `duokan-page-fullscreen`，避免 EPUBCheck 因未定義屬性失敗。
- 修正 OPF spine `itemref` 的不合法 `linear-type` 屬性：值為 `yes` /
  `no` 時會改成 EPUB 標準 `linear`，非法 `linear` 值會移除，避免
  EPUBCheck 因未知屬性或不合法值失敗。
- 修正 XHTML 廢棄 `<strike>` 元素造成的 EPUBCheck 錯誤：轉換時會改成
  HTML5/EPUB3 合法的 `<s>`，保留原本刪除線語意與內容。
- 修正 XHTML `ruby` 結構缺少 `rp` 的 EPUBCheck 錯誤：`ruby` 直屬
  `rt` 前後若缺少 fallback，會自動補入 `<rp>(</rp>` 與 `<rp>)</rp>`；
  已存在的 `rp` 不會重複加入。
- 修正 XHTML `dl` 結構不合法：`dl` 直屬裸文字會包成 `dd`，直屬
  `p`、`span`、`div` 等非 `dt` / `dd` 元素會改成 `dd`，避免 EPUBCheck
  因定義列表子層不合法失敗。
- 強化 NCX uid 同步：若 `toc.ncx` 缺少 `dtb:uid` meta 會自動補上，且
  轉換流程會在 OPF 最終清理後讀回 `unique-identifier` 對應的
  `dc:identifier` 值，再同步到 NCX，避免 NCX uid 與 OPF uid 不一致。
- 修正 XHTML `<meta>` 缺少必要 `content` 的 EPUBCheck 錯誤：`viewport`
  會從舊式 `width` / `value` 屬性搬到 `content`，缺內容的
  `Content-Type` 會改成 `<meta charset="utf-8"/>`，其他無法安全判斷且缺
  `content` 的 `name` / `http-equiv` meta 會移除。
- 修正 OPF metadata 內不合法的 `dc:meta`：轉成 EPUB3 合法的
  `<meta>`，並將常見 `opf:property` / `opf:name` 這類屬性命名空間改為
  普通 `property` / `name` 屬性，避免 `dcterms:modified`、cover metadata
  等項目因 `dc:meta` 結構被 EPUBCheck 擋下。
- 調整 `hr align="center"` 的 CSS 轉換為 `margin: 0 auto`，讓寬度不是
  100% 的水平線也能正確置中。
- 擴充 XHTML 舊式尺寸屬性修復：當 `width` / `height` 出現在 EPUB3
  不允許該屬性的元素上時，會轉成 CSS `style`；純數字會視為 px，百分比
  與常見 CSS 長度單位會保留，無法安全判斷的值才移除。
- 修正 XHTML 舊式呈現屬性的 EPUBCheck 問題：`hr size` 會轉成 CSS
  `height`、`border`、`background-color`，`hr align="center"` 會轉成左右
  `auto` margin；其他不合法的 `size` 屬性會移除，避免 EPUB3 驗證失敗。
- 修正 NCX/nav/guide 連結到錯誤資料夾或副檔名時的處理：TOC、page-list
  與 guide/landmarks 會先比對 final spine，若原目標不存在或不是 spine
  項目，會用同檔名、同 stem、`.html`/`.xhtml` 等候選規則反查實際 spine
  檔案；仍無法對應時才移除該 nav/toc 連結，避免 EPUBCheck 的非 spine
  目標錯誤。
- 轉換後清理會移除 EPUB 內的 JavaScript：刪除 XHTML `<script>` 元素、
  移除 manifest 中 `.js` 或 JavaScript media-type 項目，並刪除 package
  內殘留的 `.js` 實體檔，避免 EPUB3 驗證與閱讀器相容性問題。
- 移除 calibre 閱讀器寫入 EPUB 的書籤檔
  `META-INF/calibre_bookmarks.txt`，包含 manifest 項目與未列入 manifest 的
  實體檔。
- 參考 calibre Editor「Try to correct all fixable errors automatically」的修復
  方式，擴充轉換後的 OPF/XHTML 清理：自動修正非法或重複的 XML id、
  將 body 內裸文字包成段落、移除沒有 href 的 manifest 項目、去除重複
  manifest href 與重複 spine idref、移除 spine 的 `linear` 屬性、清掉空的
  `dc:identifier`，並在 OPF 缺少有效 `unique-identifier` 時自動補 UUID。
- 轉換後若 spine 項目副檔名本來就是 HTML/XHTML，但 OPF media-type 錯誤，
  會保守修正為 `application/xhtml+xml`，避免 EPUBCheck 將文字內容判為非
  HTML spine 項目。
- 修正缺少被引用資源時的自動尋找邏輯：若 XHTML、CSS 或 OPF 指向
  `OEBPS/Images/cover.jpg` 這類不存在路徑，轉換器會先以檔名、stem、
  資源類型與副檔名反查 EPUB 包內實際檔案，例如改指向根目錄的
  `cover.jpeg`，或改到實際存在的 CSS/HTML/圖片位置；找不到替代檔時才
  移除或保留失敗。
- 擴充缺圖修復到 SVG `<image href>` / `xlink:href`，處理封面頁常見的
  `../Images/cover.jpg` 實際應指向 `../../cover.jpeg` 的狀況。
- 新增針對畸形 EPUB2 來源的 EPUBCheck 修復：可用 recover parser 讀取破損
  XHTML/NCX，修正 OPF/NCX XML ID 與對應 spine 參照，移除或提升舊 XHTML
  `type` 屬性，讓重複元素 ID 唯一化，修正巢狀 XHTML 指向 package root
  圖片的連結，將 nav/page-list 過濾到 spine 資源，並依檔案內容偵測圖片
  manifest media type。
- 擴充 XHTML 與連結清理：移除舊 content nav、body、anchor 元素上的
  舊式 `type` 屬性，recover 修復畸形 `br` / `img` 標記，將包住 block
  list 的段落改成 `div`，並改寫大小寫與實際 package 檔案不同的本機連結。
- 新增轉換後最終引用清理：大小寫路徑修復後重新讀取 OPF，移除缺失圖片、
  清掉指向缺失檔案的壞連結，並移除本機 anchor 中不存在的 fragment。
- 依解析後的 TOC 資料重建畸形 NCX，並移除舊 landmarks self-fragment 連結，
  避免 EPUBCheck 將其視為指向非 spine 內容的引用。
- 會將已存在但缺少 OPF manifest 宣告的被引用資源補進 manifest，包括
  XHTML 內容引用的圖片檔。
- 轉換後清理 OPF manifest：移除缺失 manifest 檔案、刪除已移除項目的
  spine itemref、依副檔名修正 media type、去重 `properties="nav"`，並重建
  NCX 以避免重複目標造成 playOrder 衝突。
- 以 NCX 檔案位置為基準解析 NCX 目標，percent-decode 後再比對 TOC/page-list
  連結與 spine 路徑，移除缺失 stylesheet/script 引用與缺失 same-page
  fragment，並優先保留依檔案內容偵測出的圖片 MIME type。
- 避免 NCX 目標已含 package 目錄時被重複加上前綴；當來源 TOC 項目全部被
  過濾時，會輸出結構正確的空 nav TOC。
- 重建 NCX 時，`content src` 會以 NCX 檔案為基準寫入；空 nav TOC 會補
  fallback `li`，並在 OPF `properties="nav"` 去重時優先保留產生的
  `nav.xhtml` 項目。
- 當來源 TOC 項目全部被過濾時，產生的 nav TOC 會指向第一個 spine 項目，
  而不是輸出只有文字的 fallback 項目。
- 移除常見非標準 XHTML 屬性，清掉非產生版 EPUB3 nav 的舊 TOC/nav 連結，
  並移除 nav 或非 XHTML 資源上殘留的 `scripted` manifest property。
