import logging

from fastapi import APIRouter, Body, Path, Query
from schemas.dandanplay.v2 import (
    AnimeTypeEnum,
    CommentResSchema,
    GetBangumiResSchema,
    MatchBodySchema,
    MatchResSchema,
    SearchAnimeResSchema,
)

router = APIRouter(tags=['DanDanPlay'], prefix='/dandanplay/bilibili')

logger = logging.getLogger(__file__)


@router.post('/api/v2/match', summary='DanDanPlay Bilibili 文件识别', response_model=MatchResSchema)
async def match(body: MatchBodySchema | None = Body(None)):
    if body is None:
        body = MatchBodySchema.model_validate({})

    logger.debug(f'[dandanplay bilbili match] req {body}')
    matched = [
        {
            'episodeId': 1,
            'animeId': 1,
            'animeTitle': body.fileName if body else 'title',
            'episodeTitle': body.fileName if body else 'title',
            'typeDescription': body.fileName if body else 'title',
            'imageUrl': 'https://i1.hdslb.com/bfs/bangumi/image/132625c2e6783d1b7df32fb1781180836f32e0a5.png',
        }
    ]
    payload = {'isMatched': True, 'matched': matched}
    logger.debug(f'[dandanplay bilbili match] res {payload}')
    return payload


@router.get(
    '/api/v2/comment/{episodeId}',
    summary='DanDanPlay Bilibili 获取指定弹幕库的所有弹幕',
    response_model=CommentResSchema,
)
async def comment(
    episodeId: int = Path(..., description='弹幕库编号'),
    from_: int = Query(0, description='起始弹幕编号，忽略此编号以前的弹幕。默认值为0', alias='from'),
    withRelated: bool = Query(False, description='是否同时获取关联的第三方弹幕。默认值为false'),
    chConvert: int = Query(0, description='中文简繁转换。0-不转换，1-转换为简体，2-转换为繁体。'),
):
    comments: list[dict] = []
    payload = {'count': 0, 'comments': comments}
    for n in range(1, 1800):
        comment = {'cid': n, 'p': f'{n},1,16777215,{n}', 'm': str(n)}
        comments.append(comment)
    payload['count'] = len(comments)
    return payload


@router.get(
    '/api/v2/search/anime', summary='DanDanPlay Bilibili 根据关键词搜索作品', response_model=SearchAnimeResSchema
)
async def search_anime(
    keyword: str = Query(
        ..., min_length=2, description='关键词中的空格将被认定为 AND 条件，其他字符将被作为原始字符去搜索。'
    ),
    type: AnimeTypeEnum | None = Query(None),
):
    payload = {
        'errorCode': 0,
        'success': True,
        'errorMessage': None,
        'animes': [
            {
                'animeId': 1,
                'bangumiId': '1',
                'animeTitle': keyword,
                'type': 'other',
                'episodeCount': 150,
                'rating': 10,
                'isFavorited': False,
            },
        ],
    }

    return payload


@router.get(
    '/api/v2/bangumi/{bangumiId}', summary='DanDanPlay Bilibili 获取番剧详情', response_model=GetBangumiResSchema
)
async def bangumi(bangumiId: str = Path(..., description='作品编号')):
    payload = {
        'errorCode': 0,
        'success': True,
        'errorMessage': None,
        'bangumi': {
            'animeId': 1,
            'bangumiId': '1',
            'animeTitle': '凡人修仙传',
            'imageUrl': 'https://i1.hdslb.com/bfs/bangumi/image/132625c2e6783d1b7df32fb1781180836f32e0a5.png',
            'searchKeyword': '凡人修仙传',
            'isOnAir': True,
            'airDay': 0,
            'isFavorited': False,
            'isRestricted': False,
            'rating': 10,
            'userRating': 10,
            'type': 'tvseries',
            'typeDescription': '凡人修仙传',
            'titles': [{'language': 'cn', 'title': '凡人修仙传'}],
            'episodes': [
                {
                    'seasonId': None,
                    'episodeId': 1,
                    'episodeTitle': '凡人修仙传',
                    'episodeNumber': '凡人修仙传',
                },
            ],
            'summary': '凡人修仙传',
            'episodeCount': 150,
        },
    }

    return payload
