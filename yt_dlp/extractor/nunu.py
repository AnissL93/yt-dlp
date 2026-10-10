from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    clean_html,
    join_nonempty,
    parse_qs,
    url_or_none,
    urljoin,
)
from ..utils.traversal import traverse_obj


class NunuIE(InfoExtractor):
    IE_NAME = 'nunu'
    IE_DESC = '努努影院 (nunu.in, nunuyy*.com)'
    _VALID_URL = r'https?://(?:www\.)?(?P<host>nunu\.in|nunuyy\d*\.com)/vod/(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'https://www.nunuyy5.com/vod/202620048.html',
        'info_dict': {
            'id': '202620048-20261010b',
            'ext': 'mp4',
            'title': '披荆斩棘2026 20261010下',
            'series': '披荆斩棘2026',
            'series_id': '202620048',
            'episode': '20261010下',
            'description': r're:^披荆斩棘2026资源由努努影院',
            'thumbnail': r're:^https?://.+\.jpg',
        },
        'params': {'skip_download': 'm3u8'},
        'expected_warnings': ['Failed to download m3u8 information'],
    }, {
        'url': 'https://www.nunuyy5.com/vod/202620048.html?s=20261010',
        'only_matching': True,
    }, {
        'url': 'https://www.nunu.in/vod/202620048.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        host, series_id = self._match_valid_url(url).group('host', 'id')
        webpage = self._download_webpage(url, series_id)

        ep_slug = traverse_obj(parse_qs(url), ('s', -1)) or self._search_regex(
            r"""\.replace\(\s*['"]\{1\}['"]\s*,\s*['"]([^'"]+)""", webpage, 'episode slug')
        video_id = f'{series_id}-{ep_slug}'
        data = self._download_json(
            f'https://www.{host}/nnvod/{video_id}', video_id, headers={'Referer': url})

        formats = []
        for play in traverse_obj(data, ('video_plays', lambda _, v: url_or_none(v['play_data']))):
            formats.extend(self._extract_m3u8_formats(
                play['play_data'], video_id, 'mp4', m3u8_id=play.get('src_site') or 'hls', fatal=False))
        if not formats:
            raise ExtractorError('No playable sources found', expected=True)

        series = clean_html(self._search_regex(
            r'<h1[^>]+class="product-title"[^>]*>\s*([^<]+)', webpage, 'title', fatal=False))
        episode = clean_html(self._search_regex(
            rf'ep_slug="{ep_slug}"[^>]*>\s*<a[^>]*>([^<]+)', webpage, 'episode', fatal=False))
        return {
            'id': video_id,
            'title': join_nonempty(series, episode, delim=' ') or video_id,
            'series': series,
            'series_id': series_id,
            'episode': episode,
            'description': self._html_search_meta('description', webpage),
            'thumbnail': urljoin(url, self._search_regex(
                r'<img[^>]+src="([^"]+)"[^>]+class="thumb', webpage, 'thumbnail', fatal=False)),
            'formats': formats,
        }
