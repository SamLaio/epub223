from lxml import etree
from epub3itizer.conversion import remove_known_source_ad_paragraphs, XHTML_NS


def test_exact_forum_prefix_keeps_body_and_unsafe_variants():
    lines = ['★—————————————————————————————————★', '', '|歡迎加入典盡春衣畫流年小說羣|', '',
             '|羣號碼：75687572微信訂閱號：典盡春衣畫流年（每日推薦）|', '',
             '「進羣請報兩本小說書名字敲門，爲防小號空號廣告，預設要拿資料全的大號加羣哦。」', '',
             '【附：本小說來自網際網路,本人不做任何負責,小說內容版權歸作者所有】', '',
             '★—————————————————————————————————★']
    for kind in ('exact', 'different', 'missing', 'anchor', 'mixed', 'quoted', 'comment'):
        values = list(lines)
        if kind == 'different': values[4] = values[4].replace('75687572', '11111111')
        if kind == 'missing': values.pop(5)
        if kind == 'mixed': values[8] += '正文句子。'
        if kind == 'quoted': values.insert(0, '他引用以下宣傳：')
        root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><body>'+''.join(f'<p>{v}</p>' for v in values)+'<p>書名：她的小梨渦</p><p>作者：唧唧的貓</p><p>第一章正文</p></body></html>')
        if kind == 'anchor': root.find(f'{{{XHTML_NS}}}body')[2].set('id', 'note')
        if kind == 'comment': root.find(f'{{{XHTML_NS}}}body').insert(2, etree.Comment('保留註解'))
        prior = ''.join(root.itertext())
        remove_known_source_ad_paragraphs(root)
        text = ''.join(root.itertext())
        assert text == ('書名：她的小梨渦作者：唧唧的貓第一章正文' if kind == 'exact' else prior)
        remove_known_source_ad_paragraphs(root)
        assert ''.join(root.itertext()) == text


def test_comment_among_first_eleven_nodes_does_not_skip_title_normalization():
    from epub3itizer.conversion import collect_doc_features
    root = etree.fromstring(f'<html xmlns="{XHTML_NS}"><head><title/></head><body><!--Word註解-->'+''.join(f'<p>正文{i}</p>' for i in range(12))+'</body></html>')
    prior = ''.join(root.find(f'{{{XHTML_NS}}}body').itertext())
    output = etree.fromstring(collect_doc_features(root, 'chapter.xhtml')[0].encode())
    assert output.find(f'{{{XHTML_NS}}}head/{{{XHTML_NS}}}title').text == 'chapter.xhtml'
    assert ''.join(output.find(f'{{{XHTML_NS}}}body').itertext()) == prior
