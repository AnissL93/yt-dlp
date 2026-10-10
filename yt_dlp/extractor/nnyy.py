import re

from .common import InfoExtractor
from ..utils import (
    clean_html,
    get_element_by_class,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class NnyyIE(InfoExtractor):
    IE_NAME = 'nnyy'
    IE_DESC = '努努影院 (nnyy.in)'
    _VALID_URL = r'https?://(?:www\.)?nnyy\.in/_gp/(?P<series_id>\d+)/(?P<id>[^/?#]+)'
    _TESTS = [{
        'url': 'https://nnyy.in/_gp/20154273/20150418',
        'info_dict': {
            'id': '20150418',
            'ext': 'mp4',
            'title': '20150418',
            'series_id': '20154273',
            'episode': '20150418',
        },
        'params': {'skip_download': 'm3u8'},
        'expected_warnings': ['Failed to download m3u8 information'],
    }]

    def _real_extract(self, url):
        series_id, video_id = self._match_valid_url(url).group('series_id', 'id')
        data = self._download_json(url, video_id, headers={'Referer': 'https://nnyy.in/'})

        formats = []
        # Each source is a mirror on a different CDN; some are dead, geo-blocked or have
        # playlists pointing at dead segment hosts, so keep the site's own (player) order
        for idx, play in enumerate(traverse_obj(data, ('video_plays', lambda _, v: url_or_none(v['play_data'])))):
            src, src_site = play['play_data'], play.get('src_site')
            if '.m3u8' in src:
                fmts = self._extract_m3u8_formats(src, video_id, 'mp4', m3u8_id=src_site, fatal=False)
            else:
                fmts = [{'url': src, 'format_id': src_site}]
            for f in fmts:
                f['preference'] = -idx
            formats.extend(fmts)

        return {
            'id': video_id,
            'title': video_id,
            'series_id': series_id,
            'episode': video_id,
            'formats': formats,
        }


class NnyyPlaylistIE(InfoExtractor):
    IE_NAME = 'nnyy:playlist'
    _VALID_URL = r'https?://(?:www\.)?nnyy\.in/[a-z]+/(?P<id>\d+)\.html'
    _TESTS = [{
        'url': 'https://nnyy.in/zongyi/20154273.html',
        'info_dict': {
            'id': '20154273',
            'title': '我是歌手 第三季',
            'description': r're:^我是歌手 第三季资源由努努影院',
        },
        'playlist_count': 14,
    }]

    def _real_extract(self, url):
        series_id = self._match_id(url)
        webpage = self._download_webpage(url, series_id)
        series = re.sub(r'\s*\(\d{4}\)$', '', clean_html(get_element_by_class('product-title', webpage)) or '')

        entries = [
            self.url_result(
                f'https://nnyy.in/_gp/{series_id}/{ep_slug}', NnyyIE, ep_slug,
                f'{series} {ep_slug}' if series else ep_slug, series=series or None)
            for ep_slug in dict.fromkeys(re.findall(r'\bep_slug="([^"]+)"', webpage))]
        return self.playlist_result(
            entries, series_id, series or None, self._html_search_meta('description', webpage))
