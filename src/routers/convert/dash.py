import asyncio
import logging
import tempfile
import time
from pathlib import Path
from xml.etree import ElementTree

import ffmpeg
import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from schemas.adapter import HttpUrl

router = APIRouter(tags=["Utils"], prefix="/convert/dash")

logger = logging.getLogger(__file__)

MPD_NS = {"mpd": "urn:mpeg:dash:schema:mpd:2011"}


def _parse_mpd(content: str, base_url: str) -> tuple[str, str]:
    """从 MPD 内容中提取视频和音频流的 URL。返回 (video_url, audio_url)。"""
    root = ElementTree.fromstring(content)

    video_url = ""
    audio_url = ""

    for adaptation_set in root.findall(".//mpd:AdaptationSet", MPD_NS):
        mime_type = adaptation_set.get("mimeType", "")
        content_type = adaptation_set.get("contentType", "")

        representations = adaptation_set.findall("mpd:Representation", MPD_NS)
        if not representations:
            continue

        # 选择最高带宽的 Representation
        best = max(representations, key=lambda r: int(r.get("bandwidth", "0")))
        base_url_elem = best.find("mpd:BaseURL", MPD_NS)
        if base_url_elem is None or not base_url_elem.text:
            continue

        url = base_url_elem.text
        if not url.startswith("http"):
            url = base_url.rstrip("/") + "/" + url.lstrip("/")

        if "video" in mime_type or "video" in content_type:
            if not video_url:
                video_url = url
        elif "audio" in mime_type or "audio" in content_type:
            if not audio_url:
                audio_url = url

    if not video_url:
        raise HTTPException(status_code=400, detail="MPD 中未找到视频流")
    if not audio_url:
        raise HTTPException(status_code=400, detail="MPD 中未找到音频流")

    return video_url, audio_url


async def _fetch_mpd(dash_url: str) -> tuple[str, str]:
    """获取 MPD 并解析出视频和音频 URL。返回 (video_url, audio_url)。"""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(dash_url)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"获取 MPD 文件失败: HTTP {resp.status_code}")
        mpd_content = resp.text

    base_url = dash_url.rsplit("/", 1)[0]
    video_url, audio_url = _parse_mpd(mpd_content, base_url)
    return video_url, audio_url


@router.get("/mp4/stream", summary="dash2mp4 流式")
async def dash_to_mp4_stream(dash_url: HttpUrl = Query(..., description="MPD 文件的 URL")):
    """将 DASH MPD 中的音视频流合并为 MP4 流式返回。响应快但时长信息不准确。"""
    video_url, audio_url = await _fetch_mpd(str(dash_url))

    process = (
        ffmpeg.input(video_url)  # type: ignore
        .output(
            ffmpeg.input(audio_url),  # type: ignore
            "pipe:1",
            format="mp4",
            vcodec="copy",
            acodec="copy",
            movflags="frag_keyframe+empty_moov",
        )
        .global_args("-loglevel", "error")
        .run_async(pipe_stdout=True, pipe_stderr=True)
    )

    def stream_generator():
        try:
            while True:
                chunk = process.stdout.read(1024 * 64)
                if not chunk:
                    break
                yield chunk
        finally:
            process.stdout.close()
            stderr_output = process.stderr.read()
            process.wait()
            if process.returncode != 0 and stderr_output:
                logger.error(f"ffmpeg error: {stderr_output.decode()}")

    return StreamingResponse(
        stream_generator(),
        media_type="video/mp4",
        headers={"Content-Disposition": 'inline; filename="output.mp4"'},
    )


@router.get("/mp4", summary="dash2mp4")
async def dash_to_mp4(
    background_tasks: BackgroundTasks,
    dash_url: HttpUrl = Query(..., description="MPD 文件的 URL"),
):
    """将 DASH MPD 中的音视频流合并为 MP4 完整返回。需等待处理完成，但时长信息准确。"""
    video_url, audio_url = await _fetch_mpd(str(dash_url))

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    tmp_path = tmp.name
    tmp.close()

    def _mux():
        start = time.monotonic()
        process = (
            ffmpeg.input(video_url)
            .output(
                ffmpeg.input(audio_url),
                tmp_path,
                format="mp4",
                vcodec="copy",
                acodec="copy",
            )
            .global_args("-loglevel", "error")
            .overwrite_output()
            .run_async(pipe_stderr=True)
        )
        _, stderr_output = process.communicate()
        elapsed = time.monotonic() - start
        logger.info(f"ffmpeg mux completed in {elapsed:.2f}s")
        return process.returncode, stderr_output

    try:
        returncode, stderr_output = await asyncio.to_thread(_mux)
        if returncode != 0:
            logger.error(f"ffmpeg error: {stderr_output.decode()}")
            raise HTTPException(status_code=500, detail="音视频合并失败")
    except HTTPException:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="音视频合并失败")

    background_tasks.add_task(Path(tmp_path).unlink, missing_ok=True)
    return FileResponse(tmp_path, media_type="video/mp4", filename="output.mp4")
