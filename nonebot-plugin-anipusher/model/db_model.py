# 导入必要的模块
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal


class EmbyItem(BaseModel):
    """
    Emby媒体项数据模型，用于存储从Emby服务器获取的媒体信息
    继承自BaseDBModel，用于表示Emby中的电影、电视剧等媒体内容
    """
    id: int | None = Field(default=None, description="主键ID",
                           primary_key=True)  # type: ignore
    send_status: int = Field(default=0, ge=0, le=1,
                             description="发送状态: 0-未发送, 1-已发送")
    timestamp: datetime | None = Field(default=None, description="时间戳")
    type: Literal["Movie", "Episode", "Series"] | None = Field(
        default=None, description="媒体类型")
    title: str | None = Field(default=None, description="标题")
    description: str | None = Field(default=None, description="描述")
    season: int | None = Field(default=None, ge=0, description="季度")
    episode: int | None = Field(default=None, ge=0, description="集数")
    episode_title: str | None = Field(default=None, description="集标题")
    genres: str | None = Field(default=None, description="流派")
    score: str | None = Field(default=None, description="评分")
    tmdb_id: int | None = Field(default=None, description="TMDB ID")
    imdb_id: str | None = Field(default=None, description="IMDB ID")
    tvdb_id: int | None = Field(default=None, description="TVDB ID")
    series_id: int | None = Field(default=None, description="剧集ID")
    season_id: int | None = Field(default=None, description="季度ID")
    episode_id: int | None = Field(default=None, description="单集ID")
    series_tag: str | None = Field(default=None, description="系列标签")
    season_tag: str | None = Field(default=None, description="季度标签")
    episode_tag: str | None = Field(default=None, description="单集标签")
    server_name: str | None = Field(default=None, description="服务器名称")
    server_id: str | None = Field(default=None, description="服务器ID")
    merged_episode: int = Field(default=0, ge=0, description="合并剧集数")
    raw_data: str | None = Field(default=None, description="原始数据")

    # 在Config类中添加自定义参数的配置
    class Config:
        # 验证赋值操作
        validate_assignment = True


class AniRssItem(BaseModel):
    """
    AniRSS条目数据模型，用于存储从RSS源获取的动漫更新信息
    继承自BaseDBModel，包含动漫的标题、评分、集数等详细信息
    """
    id: int | None = Field(default=None, description="主键ID",
                           primary_key=True)  # type: ignore
    send_status: int = Field(default=0, ge=0, le=1,
                             description="发送状态: 0-未发送, 1-已发送")
    timestamp: datetime | None = Field(default=None, description="时间戳")
    action: str | None = Field(default=None, description="动作类型")
    title: str | None = Field(default=None, description="标题")
    jp_title: str | None = Field(default=None, description="日文标题")
    tmdb_title: str | None = Field(default=None, description="TMDB标题")
    score: float | None = Field(default=None, ge=0, le=10, description="评分")
    tmdb_id: int | None = Field(default=None, description="TMDB ID")
    tmdb_url: str | None = Field(default=None, description="TMDB链接")
    bangumi_url: str | None = Field(default=None, description="Bangumi链接")
    season: int | None = Field(default=None, ge=0, description="季度")
    episode: int | None = Field(default=None, ge=0, description="集数")
    tmdb_episode_title: str | None = Field(default=None, description="TMDB集标题")
    bangumi_episode_title: str | None = Field(
        default=None, description="Bangumi集标题")
    bangumi_jpepisode_title: str | None = Field(
        default=None, description="Bangumi日文集标题")
    subgroup: str | None = Field(default=None, description="字幕组")
    progress: str | None = Field(default=None, description="进度")
    premiere: str | None = Field(default=None, description="首播日期")
    download_path: str | None = Field(default=None, description="下载路径")
    text: str | None = Field(default=None, description="文本")
    image_url: str | None = Field(default=None, description="图片链接")
    raw_data: str | None = Field(default=None, description="原始数据")

    # 在Config类中添加自定义参数的配置
    class Config:
        # 验证赋值操作
        validate_assignment = True


class AnimeItem(BaseModel):
    """
    动漫条目数据模型，用于存储动漫的综合信息
    继承自BaseDBModel，整合了来自多个源的动漫数据，并包含订阅者信息
    """
    tmdb_id: int | None = Field(
        default=None, description="TMDB ID", primary_key=True)  # type: ignore
    emby_title: str | None = Field(default=None, description="Emby标题")
    tmdb_title: str | None = Field(default=None, description="TMDB标题")
    score: float | None = Field(default=None, ge=0, le=10, description="评分")
    genres: str | None = Field(default=None, description="流派")
    tmdb_url: str | None = Field(default=None, description="TMDB链接")
    bangumi_url: str | None = Field(default=None, description="Bangumi链接")
    ainrss_image_url: str | None = Field(
        default=None, description="AniRSS图片链接")
    emby_image_url: str | None = Field(default=None, description="Emby图片链接")
    emby_series_url: str | None = Field(default=None, description="Emby系列链接")
    group_subscriber: dict = Field(default={}, description="群组订阅者")
    private_subscriber: list = Field(default=[], description="私信订阅者")

    # 在Config类中添加自定义参数的配置
    class Config:
        # 验证赋值操作
        validate_assignment = True
