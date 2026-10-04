import hashlib
import urllib.parse

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    int_or_none,
    join_nonempty,
    parse_iso8601,
    url_or_none,
)
from ..utils.traversal import traverse_obj


class YfspIE(InfoExtractor):
    IE_NAME = 'yfsp'
    IE_DESC = '爱壹帆 (yfsp.tv)'
    _VALID_URL = r'https?://(?:www\.|m\.)?yfsp\.tv/play/(?P<series_id>\w+)\?(?:[^#]*&)?id=(?P<id>\w+)'
    _TESTS = [{
        'url': 'https://www.yfsp.tv/play/NjvfTz4MVG6?id=JQiEv4zRUhQ',
        'info_dict': {
            'id': 'JQiEv4zRUhQ',
            'ext': 'mp4',
            'title': '披荆斩棘2026 20260830(加更版)',
            'series': '披荆斩棘2026',
            'series_id': 'NjvfTz4MVG6',
            'episode': '20260830(加更版)',
            'description': r're:^《披荆斩棘2026》本季集结28位嘉宾',
            'thumbnail': r're:^https?://.+',
            'duration': 2528,
            'timestamp': int,
            'upload_date': str,
        },
        'params': {'skip_download': 'm3u8'},
    }]

    def _call_api(self, path, video_id, params, pconfig):
        query = '&'.join(f'{k}={v}' for k, v in params.items())
        vv = hashlib.md5(
            f'{pconfig["publicKey"]}&{query.lower()}&{pconfig["privateKey"][0]}'.encode()).hexdigest()
        resp = self._download_json(
            f'https://m10.yfsp.tv/v3/{path}?{urllib.parse.urlencode(params)}&vv={vv}&pub={pconfig["publicKey"]}',
            video_id, note=f'Downloading {path} JSON', headers={'Referer': 'https://www.yfsp.tv/'})
        if resp.get('ret') != 200 or traverse_obj(resp, ('data', 'code')) != 0:
            raise ExtractorError(f'API error: {traverse_obj(resp, ("data", "msg")) or resp.get("msg")}')
        return traverse_obj(resp, ('data', 'info', 0, {dict})) or {}

    def _real_extract(self, url):
        series_id, video_id = self._match_valid_url(url).group('series_id', 'id')
        webpage = self._download_webpage(url, video_id)
        pconfig = traverse_obj(self._search_json(
            r'var\s+injectJson\s*=', webpage, 'inject json', video_id),
            ('config', 0, 'pConfig', {dict}))
        if not pconfig:
            raise ExtractorError('Unable to find signing keys')

        detail = self._call_api('video/detail', series_id, {
            'cinema': 1, 'device': 1, 'player': 'CkPlayer', 'tech': 'HLS', 'country': 'HU',
            'lang': 'cns', 'v': 1, 'id': series_id, 'region': 'GL.'}, pconfig)
        play = self._call_api('video/play', video_id, {
            'cinema': 1, 'id': video_id, 'a': 0, 'lang': 'cns', 'usersign': 1,
            'region': 'GL.', 'device': 1, 'isMasterSupport': 1}, pconfig)

        formats = []
        for clarity in traverse_obj(play, ('clarity', lambda _, v: url_or_none(v['path']['result']))):
            fmts = self._extract_m3u8_formats(
                clarity['path']['result'], video_id, 'mp4', m3u8_id=join_nonempty('hls', clarity.get('title')),
                fatal=False) if clarity['path'].get('isHls') else [{'url': clarity['path']['result']}]
            for f in fmts:
                f.setdefault('height', int_or_none(clarity.get('title')))
            formats.extend(fmts)
        if not formats and traverse_obj(play, ('clarity', ..., 'isVIP')):
            self.raise_login_required('This video requires a VIP account')

        series = detail.get('title')
        episode = play.get('mediaTitle')
        return {
            'id': video_id,
            'title': join_nonempty(series, episode, delim=' ') or video_id,
            'series': series,
            'series_id': series_id,
            'episode': episode,
            'formats': formats,
            'duration': traverse_obj(play, ('customData', 't', {int_or_none})),
            **traverse_obj(detail, {
                'description': ('contxt', {str}),
                'thumbnail': ('imgPath', {url_or_none}),
                'timestamp': ('addTime', {parse_iso8601}),
            }),
        }
