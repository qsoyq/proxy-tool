from enum import Enum

from pydantic import BaseModel, Field


class BaseResSchema(BaseModel):
    errorCode: int = Field(
        0, description='错误代码，0表示没有发生错误，非0表示有错误，详细信息会包含在errorMessage属性中'
    )
    success: bool = Field(True, description='接口是否调用成功')
    errorMessage: str | None = Field(None, description='当发生错误时，说明错误具体原因')


class MatchModeEnum(str, Enum):
    hashAndFileName = 'hashAndFileName'
    fileNameOnly = 'fileNameOnly'
    hashOnly = 'hashOnly'


class AnimeTypeEnum(str, Enum):
    tvseries = 'tvseries'
    tvspecial = 'tvspecial'
    ova = 'ova'
    movie = 'movie'
    musicvideo = 'musicvideo'
    web = 'web'
    other = 'other'
    jpmovie = 'jpmovie'
    jpdrama = 'jpdrama'
    unknown = 'unknown'
    tmdbtv = 'tmdbtv'
    tmdbmovie = 'tmdbmovie'


class MatchBodySchema(BaseModel):
    fileName: str | None = Field(None, description='视频文件名，不包含文件夹名称和扩展名，特殊字符需进行转义。')
    fileHash: str | None = Field(None, description='文件前16MB (16x1024x1024 Byte) 数据的32位MD5结果，不区分大小写。')
    fileSize: int | None = Field(None, description='文件总长度，单位为Byte。')
    videoDuration: int | None = Field(None, description='[可选]32位整数的视频时长，单位为秒。默认为0。')
    matchMode: MatchModeEnum | None = Field(None, description='[可选]匹配模式。')


class MatchDetailSchema(BaseModel):
    episodeId: int = Field(..., description='弹幕库ID')
    animeId: int = Field(..., description='作品ID')
    animeTitle: str | None = Field(None, description='作品标题')
    episodeTitle: str | None = Field(None, description='剧集标题')
    type: AnimeTypeEnum = Field(
        AnimeTypeEnum.other, description='视频文件名，不包含文件夹名称和扩展名，特殊字符需进行转义。'
    )
    typeDescription: str | None = Field(None, description='类型描述')
    shift: float = Field(
        0, description='弹幕偏移时间（弹幕应延迟多少秒出现）。此数字为负数时表示弹幕应提前多少秒出现。'
    )
    imageUrl: str | None = Field(None, description='此作品的海报图片地址')


class MatchResSchema(BaseResSchema):
    isMatched: bool = Field(..., description='是否已精确关联到某个弹幕库')
    matched: list[MatchDetailSchema] = Field([], description='搜索匹配的结果')


class CommentSchema(BaseModel):
    """
    弹幕出现时间，单位为秒
    弹幕模式：1-普通弹幕，4-顶部弹幕，5-底部弹幕
    弹幕颜色，计算方式为 Rx255x255+Gx255+B
    """

    cid: int = Field(..., description='弹幕ID')
    p: str | None = Field(None, description='弹幕参数（出现时间,模式,颜色,用户ID）')
    m: str | None = Field(None, description='弹幕内容')


class CommentResSchema(BaseModel):
    count: int = Field(..., description='弹幕数量')
    comments: list[CommentSchema] = Field([], description='弹幕列表')


class AnimeSchema(BaseModel):
    animeId: int = Field(..., description='作品ID')
    bangumiId: str | None = Field(None, description='作品ID（新）')
    animeTitle: str | None = Field(None, description='作品标题')
    imageUrl: str | None = Field(None, description='此作品的海报图片地址')
    type: AnimeTypeEnum = Field(
        AnimeTypeEnum.other, description='视频文件名，不包含文件夹名称和扩展名，特殊字符需进行转义。'
    )
    typeDescription: str | None = Field(None, description='类型描述')
    startDate: str | None = Field(None, description='上映日期')
    episodeCount: int = Field(..., description='剧集总数')
    rating: float = Field(..., description='此作品的综合评分（0-10）', ge=0, le=10)
    isFavorited: bool = Field(False, description='当前用户是否已关注此作品')


class SearchAnimeResSchema(BaseResSchema):
    animes: list[AnimeSchema] | None = Field([], description='作品列表')


class BangumiTitleSchema(BaseModel):
    language: str | None = Field(None, description='语言')
    title: str | None = Field(None, description='标题')


class BangumiEpisodeSeason(BaseModel):
    id: str | None = Field(None, description='季度ID')
    airDate: str | None = Field(None, description='上映日期')
    name: str | None = Field(None, description='季度名称')
    episodeCount: int = Field(..., description='剧集数量')
    summary: str | None = Field(None, description='季度简介')


class BangumiEpisode(BaseModel):
    seasonId: str | None = Field(None, description='季度ID（如果为空表示只有一个季度）')
    episodeId: int = Field(..., description='弹幕库ID')
    episodeTitle: str | None = Field(None, description='季度ID（如果为空表示只有一个季度）')
    episodeNumber: str | None = Field(None, description='剧集短标题（可以用来排序，非纯数字，可能包含字母）')
    lastWatched: str | None = Field(None, description='上次观看时间（服务器时间，即北京时间）')
    airDate: str | None = Field(None, description='本集上映时间（当地时间）')


class BangumiSchema(AnimeSchema):
    searchKeyword: str | None = Field(None, description='搜索关键词')
    isOnAir: bool = Field(..., description='是否正在连载中')
    airDay: int = Field(..., description='周几上映，0代表周日，1-6代表周一至周六', ge=0, le=6)
    isRestricted: bool = Field(..., description='是否为限制级别的内容（例如属于R18分级）')
    titles: list[BangumiTitleSchema] | None = Field(None, description='作品标题')
    seasons: list[BangumiEpisodeSeason] | None = Field(
        None, description='作品季度列表。可能为空，仅对部分源（如TMDB源）有效'
    )
    episodes: list[BangumiEpisode] | None = Field(None, description='剧集列表')
    summary: str | None = Field(None, description='番剧简介')
    intro: str | None = Field(None, description='短简介（Staff简介或剧情简介）')
    metadata: list[str] | None = Field(None, description='番剧元数据（名称、制作人员、配音人员等）')
    bangumiUrl: str | None = Field(None, description='Bangumi.tv页面地址')
    userRating: int = Field(..., description='用户个人评分（0-10）', ge=0, le=10)


class GetBangumiResSchema(BaseResSchema):
    bangumi: BangumiSchema | None = Field(None, description='番剧详情')
