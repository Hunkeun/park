# -*- coding: utf-8 -*-
"""
publisher/books_master.json 통합 빌더.

121권 통합:
- 시즌1 본권 10권 (ISBN 9791199881...)
- 시즌1 종합책 1권 (ISBN 9791176580007)
- 시즌2 본권 100권 (ISBN 9791124569...)
- 시즌2 종합책 10권 (ISBN 9791176580014~0106, G01~G10)

소스:
- batch_books.json (시즌2 본권 메타)
- batch_books_g01_omnibus.json ~ batch_books_g10_omnibus.json (시즌2 종합책 메타)
- isbn_list.json (시즌2 본권 100 ISBN)
- isbn_list_100omnibus.json (시즌2 종합책 10 ISBN)
- isbn_list_10books.json (시즌1 본권 10 + 종합책 1 ISBN)
- ebook_video_robot.py SEASONS[1].books (시즌1 본권 제목)
- ~/Downloads/전자책/ (본권 epub + 표지)
- ~/Downloads/_100권_확장본_검수/ (시즌2 본권 부크크 확장본)
- tmp/ (종합책 epub)
"""
# PATCHED:utf8-stdout-v1
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding='utf-8')
    _sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass


import json
import os
import re
from pathlib import Path


S1_BOOKS = [
    "AI 시대 영성 상담사를 만나다",
    "산을 옮길만한 믿음",
    "아름다운 감성을 사모하자",
    "다수의 횡포를 직관하라",
    "새술은 새부대에 담아야",
    "카이로스와 자유의지",
    "진동 에너지와 치유",
    "이스라엘 어느 왕의 덤 인생",
    "죽음의 역설",
    "이 세상과 저 세상",
]
S1_OMNIBUS_TITLE = "AI 시대를 살아가는 영성"

S2_PRICE_MAIN = 2000
S2_PRICE_OMNIBUS = 7000
S1_PRICE_MAIN = 2000
S1_PRICE_OMNIBUS = 7000
S1_PUBDATE_MAIN = '2026-04-25'


def s2_pubdate(seq):
    if 1 <= seq <= 57: return '2026-05-02'
    if 58 <= seq <= 91: return '2026-05-16'
    if 92 <= seq <= 100: return '2026-05-30'
    return None


GROUPS = {
    'G01': {'name': '천국과 영계', 'theme': '사후세계'},
    'G02': {'name': '알고리즘 시대의 영성', 'theme': 'AI·디지털'},
    'G03': {'name': '겨자씨에서 산까지', 'theme': '단단한 믿음'},
    'G04': {'name': '발자국과 눈물', 'theme': '성경 인물'},
    'G05': {'name': '흉터 위의 빛', 'theme': '내면 치유'},
    'G06': {'name': '광야의 외침', 'theme': '시대 분별'},
    'G07': {'name': '바람과 불', 'theme': '성령'},
    'G08': {'name': '무릎의 자리', 'theme': '기도'},
    'G09': {'name': '곁에 두신 분들', 'theme': '관계'},
    'G10': {'name': '이미, 그러나 아직', 'theme': '하나님 나라'},
}

EBOOK_DIR = os.path.expanduser('~/Downloads/전자책')
EXTENSION_DIR = os.path.expanduser('~/Downloads/_100권_확장본_검수')
S1_EXTENSION_DIR = os.path.expanduser('~/Downloads/_부크크검수')
OMNIBUS_DIR = 'tmp'
COVER_DIRS = [
    os.path.expanduser('~/Downloads/전자책'),
    os.path.expanduser('~/Downloads/전자책/커버_추출'),
]
COVER_SUFFIXES = ('_cover.jpg', '_표지.jpg', '_cover.png', '_표지.png')


def slugify(title):
    """파일명용 슬러그 (공백 → _)."""
    return title.replace(' ', '_')


def find_epub(title, base_dir, omnibus=False, prefer_date=None):
    """제목으로 epub 파일 찾기.
    omnibus=False: '_종합책'이 들어간 파일은 제외
    omnibus=True: '_종합책'이 들어간 파일만
    prefer_date: 'YYYY-MM-DD' 형식. 같은 제목 여러 빌드가 있을 때 우선 매칭
    """
    pattern = slugify(title)
    p = Path(base_dir)
    if not p.exists():
        return None, None
    candidates = []
    for f in p.glob('*.epub'):
        if '.bak' in f.name:
            continue
        if not f.name.startswith(pattern):
            continue
        is_omni = '_종합책' in f.name or '_omnibus' in f.name
        if omnibus and not is_omni:
            continue
        if not omnibus and is_omni:
            continue
        candidates.append(f.name)
    if not candidates:
        return None, None

    fname = None
    if prefer_date:
        prefer_str = prefer_date.replace('-', '')
        for c in candidates:
            if prefer_str in c:
                fname = c
                break
    if fname is None:
        candidates.sort(reverse=True)
        fname = candidates[0]

    m = re.search(r'(\d{8})', fname)
    pubdate = None
    if m:
        d = m.group(1)
        pubdate = f'{d[:4]}-{d[4:6]}-{d[6:8]}'
    return fname, pubdate


def find_cover(title):
    """시즌1·2 표지 모두 검색. (filename, source_dir) 튜플 반환."""
    pattern = slugify(title)
    for base in COVER_DIRS:
        p = Path(base)
        if not p.exists():
            continue
        for suffix in COVER_SUFFIXES:
            for f in p.glob(f'*{suffix}'):
                if f.name.startswith(pattern):
                    return f.name, base
    return None, None


def load_youtube_map():
    """youtube_map.json 읽어서 (book_id -> youtube_id), (group -> playlist_id) 두 dict 반환.

    youtube_id가 빈 문자열이면 미업로드 → 매핑에서 제외 (책에 필드 안 붙음).
    playlist_id는 '(미확정...)'으로 시작하면 제외.
    """
    p = Path('youtube_map.json')
    if not p.exists():
        return {}, {}
    with open(p, encoding='utf-8') as f:
        ym = json.load(f)
    book_yt = {}
    for b in ym.get('books', []):
        yid = (b.get('youtube_id') or '').strip()
        if not yid:
            continue
        season = b['season']
        num = b['num']
        if season == 1:
            book_id = f's1-{num:02d}'
        else:
            book_id = f's2-{num:03d}'
        book_yt[book_id] = yid
    playlist = {}
    for gid, pl in (ym.get('playlists') or {}).items():
        pid = (pl.get('id') or '').strip()
        if not pid or pid.startswith('('):
            continue
        playlist[gid] = {'id': pid, 'title': pl.get('title', '')}
    return book_yt, playlist


def build():
    books = []

    with open('isbn_list_10books.json', encoding='utf-8') as f:
        s1_isbn = json.load(f)
    with open('isbn_list.json', encoding='utf-8') as f:
        s2_isbn = json.load(f)
    with open('isbn_list_100omnibus.json', encoding='utf-8') as f:
        s2_omni_isbn = json.load(f)
    with open('batch_books.json', encoding='utf-8') as f:
        s2_data = json.load(f)

    book_yt, playlist = load_youtube_map()

    for i, title in enumerate(S1_BOOKS, 1):
        epub, _ = find_epub(title, S1_EXTENSION_DIR)
        if not epub:
            epub, _ = find_epub(title, EBOOK_DIR)
        cover, cover_dir = find_cover(title)
        bid = f's1-{i:02d}'
        rec = {
            'id': bid,
            'season': 1,
            'type': 'main',
            'seq': i,
            'title': title,
            'isbn': s1_isbn.get(f'10-{i}'),
            'price': S1_PRICE_MAIN,
            'publish_date': S1_PUBDATE_MAIN,
            'author': 'AI, 박헌근',
            'publisher': 'AI 시대 영성',
            'format': '전자책 (EPUB)',
            'epub_filename': epub,
            'cover_filename': cover,
            'cover_source_dir': cover_dir,
        }
        if bid in book_yt:
            rec['youtube_id'] = book_yt[bid]
        books.append(rec)

    omni_epub, omni_pub = find_epub(S1_OMNIBUS_TITLE, OMNIBUS_DIR, omnibus=True, prefer_date='2026-05-30')
    s1_omni_rec = {
        'id': 's1-omnibus',
        'season': 1,
        'type': 'omnibus',
        'seq': 1,
        'title': S1_OMNIBUS_TITLE,
        'subtitle': '시즌 1 열 권을 한 권으로',
        'isbn': s1_isbn.get('10-omnibus'),
        'price': S1_PRICE_OMNIBUS,
        'publish_date': omni_pub or '2026-05-30',
        'author': 'AI, 박헌근',
        'publisher': 'AI 시대 영성',
        'format': '전자책 (EPUB)',
        'epub_filename': omni_epub,
    }
    if 'S1' in playlist:
        s1_omni_rec['playlist_id'] = playlist['S1']['id']
        s1_omni_rec['playlist_title'] = playlist['S1']['title']
    books.append(s1_omni_rec)

    for group_data in s2_data:
        gid_int = group_data['group']
        gid = f"G{gid_int:02d}"
        gmeta = GROUPS[gid]
        for b in group_data['books']:
            local_seq = b['seq']
            global_seq = (gid_int - 1) * 10 + local_seq
            epub, _ = find_epub(b['title'], EXTENSION_DIR)
            if not epub:
                epub, _ = find_epub(b['title'], EBOOK_DIR)
            cover, cover_dir = find_cover(b['title'])
            bid = f's2-{global_seq:03d}'
            rec = {
                'id': bid,
                'season': 2,
                'group': gid,
                'group_name': gmeta['name'],
                'group_theme': gmeta['theme'],
                'type': 'main',
                'seq': global_seq,
                'group_seq': local_seq,
                'title': b['title'],
                'subtitle': b['subtitle'],
                'isbn': s2_isbn.get(f'100-{global_seq}'),
                'price': S2_PRICE_MAIN,
                'publish_date': s2_pubdate(global_seq),
                'author': 'AI, 박헌근',
                'publisher': 'AI 시대 영성',
                'format': '전자책 (EPUB)',
                'summary': b.get('insight', ''),
                'keywords': b.get('keywords', ''),
                'metaphor': b.get('metaphor', ''),
                'epub_filename': epub,
                'cover_filename': cover,
                'cover_source_dir': cover_dir,
            }
            if bid in book_yt:
                rec['youtube_id'] = book_yt[bid]
            books.append(rec)

    for gid_int in range(1, 11):
        gid = f"G{gid_int:02d}"
        gmeta = GROUPS[gid]
        gpath = Path(f'batch_books_{gid.lower()}_omnibus.json')
        proj = {}
        if gpath.exists():
            with open(gpath, encoding='utf-8') as f:
                gd = json.load(f)
            proj = gd.get('project', {})

        omni_title = proj.get('title', gmeta['name'])
        epub, omni_pub = find_epub(omni_title, OMNIBUS_DIR, omnibus=True, prefer_date='2026-05-30')

        rec = {
            'id': f's2-omnibus-{gid}',
            'season': 2,
            'group': gid,
            'group_name': gmeta['name'],
            'type': 'omnibus',
            'seq': gid_int,
            'title': omni_title,
            'subtitle': proj.get('subtitle', ''),
            'isbn': s2_omni_isbn.get(f'100-omnibus-{gid}'),
            'price': S2_PRICE_OMNIBUS,
            'publish_date': proj.get('publish_date', omni_pub or '2026-05-30'),
            'author': 'AI, 박헌근',
            'publisher': proj.get('publisher', 'AI 시대 영성'),
            'format': proj.get('format_primary', '전자책 (EPUB)'),
            'epub_filename': epub,
        }
        if gid in playlist:
            rec['playlist_id'] = playlist[gid]['id']
            rec['playlist_title'] = playlist[gid]['title']
        books.append(rec)

    out = {
        'updated_at': '2026-05-01',
        'total_count': len(books),
        'breakdown': {
            'season_1_main': sum(1 for b in books if b['season']==1 and b['type']=='main'),
            'season_1_omnibus': sum(1 for b in books if b['season']==1 and b['type']=='omnibus'),
            'season_2_main': sum(1 for b in books if b['season']==2 and b['type']=='main'),
            'season_2_omnibus': sum(1 for b in books if b['season']==2 and b['type']=='omnibus'),
        },
        'missing_files': {
            'epub': [b['id'] for b in books if not b.get('epub_filename')],
            'cover': [b['id'] for b in books if b['type']=='main' and not b.get('cover_filename')],
        },
        'books': books,
    }

    os.makedirs('publisher', exist_ok=True)
    out_path = 'publisher/books_master.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    return out


if __name__ == '__main__':
    out = build()
    bd = out['breakdown']
    print(f'[완료] {out["total_count"]}권 -> publisher/books_master.json')
    print(f'  시즌1 본권:    {bd["season_1_main"]:>3d}/10')
    print(f'  시즌1 종합책:  {bd["season_1_omnibus"]:>3d}/1')
    print(f'  시즌2 본권:    {bd["season_2_main"]:>3d}/100')
    print(f'  시즌2 종합책:  {bd["season_2_omnibus"]:>3d}/10')
    miss = out['missing_files']
    if miss['epub']:
        print(f'  [경고] epub 누락 {len(miss["epub"])}건: {miss["epub"][:5]}{" ..." if len(miss["epub"])>5 else ""}')
    if miss['cover']:
        print(f'  [경고] 표지 누락 {len(miss["cover"])}건 (본권만): {miss["cover"][:5]}{" ..." if len(miss["cover"])>5 else ""}')
