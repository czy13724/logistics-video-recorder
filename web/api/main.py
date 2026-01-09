"""
物流视频录制系统 - Web API
提供RESTful API接口用于视频管理、数据统计等功能
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import cv2
from collections import Counter
import mimetypes

app = FastAPI(
    title="物流视频录制系统API",
    description="物流退货视频录制与管理系统的Web API",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置路径
BASE_DIR = Path(__file__).parent.parent.parent
VIDEOS_DIR = BASE_DIR / "videos"
REPORTS_DIR = BASE_DIR / "reports"
EXPORTS_DIR = BASE_DIR / "exports"
CONFIG_FILE = BASE_DIR / "config.json"

# 确保目录存在
VIDEOS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)


# 数据模型
class VideoRecord(BaseModel):
    tracking_number: str
    timestamp: str
    file_path: str
    duration: Optional[float] = None
    size: Optional[int] = None
    problems: Optional[List[str]] = []
    notes: Optional[str] = ""


class ProblemUpdate(BaseModel):
    problems: List[str]
    notes: str


class StatsSummary(BaseModel):
    total_videos: int
    today_videos: int
    total_problems: int
    storage_used: str
    problem_distribution: dict
    daily_trend: List[dict]


# 工具函数
def get_video_info(video_path: Path) -> dict:
    """获取视频文件信息"""
    try:
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        
        return {
            "duration": round(duration, 2),
            "size": video_path.stat().st_size,
            "modified": datetime.fromtimestamp(video_path.stat().st_mtime).isoformat()
        }
    except Exception as e:
        print(f"获取视频信息失败: {e}")
        return {"duration": 0, "size": 0, "modified": ""}


def parse_filename(filename: str) -> dict:
    """解析视频文件名，提取快递单号和时间戳"""
    # 格式: 快递单号_YYYYMMDD_HHMMSS.mp4
    try:
        name_without_ext = filename.rsplit('.', 1)[0]
        parts = name_without_ext.split('_')
        
        if len(parts) >= 3:
            tracking_number = '_'.join(parts[:-2])
            date_str = parts[-2]
            time_str = parts[-1]
            timestamp = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]} {time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
            return {
                "tracking_number": tracking_number,
                "timestamp": timestamp
            }
    except Exception as e:
        print(f"解析文件名失败: {filename}, 错误: {e}")
    
    return {
        "tracking_number": filename,
        "timestamp": datetime.now().isoformat()
    }


def load_video_metadata(tracking_number: str, timestamp: str) -> dict:
    """加载视频元数据（问题和备注）"""
    metadata_file = VIDEOS_DIR / f"{tracking_number}_{timestamp.replace(':', '').replace('-', '').replace(' ', '_')}.json"
    
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    return {"problems": [], "notes": ""}


def save_video_metadata(tracking_number: str, timestamp: str, problems: List[str], notes: str):
    """保存视频元数据"""
    metadata_file = VIDEOS_DIR / f"{tracking_number}_{timestamp.replace(':', '').replace('-', '').replace(' ', '_')}.json"
    
    metadata = {
        "problems": problems,
        "notes": notes,
        "updated_at": datetime.now().isoformat()
    }
    
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


# API路由
@app.get("/")
async def root():
    """API根路径"""
    return {
        "message": "物流视频录制系统API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/videos", response_model=List[VideoRecord])
async def get_videos(
    search: Optional[str] = Query(None, description="搜索关键词"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    has_problems: Optional[bool] = Query(None, description="是否有问题")
):
    """获取所有视频记录"""
    videos = []
    
    # 遍历videos目录下的所有mp4文件
    for video_file in VIDEOS_DIR.glob("*.mp4"):
        file_info = parse_filename(video_file.name)
        video_info = get_video_info(video_file)
        metadata = load_video_metadata(file_info["tracking_number"], file_info["timestamp"])
        
        # 过滤条件
        if search and search.lower() not in file_info["tracking_number"].lower():
            continue
        
        if start_date:
            try:
                video_date = datetime.strptime(file_info["timestamp"], "%Y-%m-%d %H:%M:%S").date()
                filter_start = datetime.strptime(start_date, "%Y-%m-%d").date()
                if video_date < filter_start:
                    continue
            except:
                pass
        
        if end_date:
            try:
                video_date = datetime.strptime(file_info["timestamp"], "%Y-%m-%d %H:%M:%S").date()
                filter_end = datetime.strptime(end_date, "%Y-%m-%d").date()
                if video_date > filter_end:
                    continue
            except:
                pass
        
        if has_problems is not None:
            if has_problems and not metadata.get("problems"):
                continue
            if not has_problems and metadata.get("problems"):
                continue
        
        videos.append(VideoRecord(
            tracking_number=file_info["tracking_number"],
            timestamp=file_info["timestamp"],
            file_path=str(video_file.name),
            duration=video_info.get("duration"),
            size=video_info.get("size"),
            problems=metadata.get("problems", []),
            notes=metadata.get("notes", "")
        ))
    
    # 按时间倒序排序
    videos.sort(key=lambda x: x.timestamp, reverse=True)
    
    return videos


@app.get("/api/videos/{tracking_number}/stream")
async def stream_video(tracking_number: str, timestamp: str):
    """流式传输视频"""
    # 构建文件名
    timestamp_clean = timestamp.replace(':', '').replace('-', '').replace(' ', '_')
    video_file = VIDEOS_DIR / f"{tracking_number}_{timestamp_clean}.mp4"
    
    if not video_file.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在")
    
    return FileResponse(
        video_file,
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename="{video_file.name}"'
        }
    )


@app.put("/api/videos/{tracking_number}/problems")
async def update_video_problems(tracking_number: str, timestamp: str, update: ProblemUpdate):
    """更新视频的问题标记和备注"""
    try:
        save_video_metadata(tracking_number, timestamp, update.problems, update.notes)
        return {"message": "更新成功", "tracking_number": tracking_number}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@app.delete("/api/videos/{tracking_number}")
async def delete_video(tracking_number: str, timestamp: str):
    """删除视频及其元数据"""
    timestamp_clean = timestamp.replace(':', '').replace('-', '').replace(' ', '_')
    video_file = VIDEOS_DIR / f"{tracking_number}_{timestamp_clean}.mp4"
    metadata_file = VIDEOS_DIR / f"{tracking_number}_{timestamp_clean}.json"
    
    deleted = []
    
    if video_file.exists():
        video_file.unlink()
        deleted.append("video")
    
    if metadata_file.exists():
        metadata_file.unlink()
        deleted.append("metadata")
    
    if not deleted:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return {"message": f"已删除: {', '.join(deleted)}", "tracking_number": tracking_number}


@app.get("/api/stats", response_model=StatsSummary)
async def get_statistics():
    """获取统计数据"""
    all_videos = []
    total_size = 0
    problem_list = []
    daily_counts = Counter()
    
    today = datetime.now().date()
    today_count = 0
    
    for video_file in VIDEOS_DIR.glob("*.mp4"):
        file_info = parse_filename(video_file.name)
        video_info = get_video_info(video_file)
        metadata = load_video_metadata(file_info["tracking_number"], file_info["timestamp"])
        
        total_size += video_info.get("size", 0)
        
        # 统计今日视频
        try:
            video_date = datetime.strptime(file_info["timestamp"], "%Y-%m-%d %H:%M:%S").date()
            date_str = video_date.strftime("%Y-%m-%d")
            daily_counts[date_str] += 1
            
            if video_date == today:
                today_count += 1
        except:
            pass
        
        # 收集问题
        if metadata.get("problems"):
            problem_list.extend(metadata["problems"])
        
        all_videos.append(file_info)
    
    # 问题分布
    problem_distribution = dict(Counter(problem_list))
    
    # 最近7天趋势
    daily_trend = []
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        daily_trend.append({
            "date": date_str,
            "count": daily_counts.get(date_str, 0)
        })
    
    return StatsSummary(
        total_videos=len(all_videos),
        today_videos=today_count,
        total_problems=len(problem_list),
        storage_used=format_size(total_size),
        problem_distribution=problem_distribution,
        daily_trend=daily_trend
    )


@app.get("/api/exports")
async def list_exports():
    """列出所有导出文件"""
    exports = []
    
    for export_file in EXPORTS_DIR.glob("*.pdf"):
        exports.append({
            "name": export_file.name,
            "type": "pdf",
            "size": format_size(export_file.stat().st_size),
            "created": datetime.fromtimestamp(export_file.stat().st_mtime).isoformat()
        })
    
    for report_file in REPORTS_DIR.glob("*.csv"):
        exports.append({
            "name": report_file.name,
            "type": "csv",
            "size": format_size(report_file.stat().st_size),
            "created": datetime.fromtimestamp(report_file.stat().st_mtime).isoformat()
        })
    
    # 按创建时间倒序
    exports.sort(key=lambda x: x["created"], reverse=True)
    
    return exports


@app.get("/api/exports/{filename}")
async def download_export(filename: str):
    """下载导出文件"""
    # 尝试从两个目录查找
    file_path = EXPORTS_DIR / filename
    if not file_path.exists():
        file_path = REPORTS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    # 获取MIME类型
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        mime_type = "application/octet-stream"
    
    return FileResponse(
        file_path,
        media_type=mime_type,
        filename=filename
    )


@app.get("/api/config")
async def get_config():
    """获取系统配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
