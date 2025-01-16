import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import dateutil.parser
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from lottery import ForumTopicInfo, generate_final_seed, generate_winning_floors, LotteryError

# 创建应用实例
app = FastAPI()

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保静态文件目录存在
static_path = Path("static")
static_path.mkdir(exist_ok=True)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")


class LotteryRequest(BaseModel):
    topic_url: str
    winners_count: int
    last_floor: Optional[int] = None


class SystemInfo(BaseModel):
    lottery_version: str
    os_info: str
    python_version: str


@app.get("/")
async def read_root():
    """提供网页首页"""
    return FileResponse('static/index.html')


@app.get("/api/system-info")
async def get_system_info():
    return SystemInfo(
        lottery_version="0.0.5",
        os_info=f"{platform.system()} {platform.release()}",
        python_version=sys.version.split()[0],
    )


@app.post("/api/draw")
async def draw_lottery(request: LotteryRequest):
    """执行抽奖"""
    try:
        # 初始化主题信息
        topic_info = ForumTopicInfo.from_url(request.topic_url)
        topic_info.fetch_topic_info()
        valid_floors = topic_info.fetch_valid_post_numbers(request.last_floor)
        total_floors = len(valid_floors)

        if total_floors < 1:
            raise HTTPException(status_code=400, detail="没有足够的参与楼层")

        # 生成获奖者
        winners_count = min(request.winners_count, total_floors)
        final_seed = generate_final_seed(topic_info, winners_count)
        winning_floors = generate_winning_floors(final_seed, valid_floors, winners_count)

        # 格式化结果
        created_time = dateutil.parser.parse(topic_info.created_at).astimezone()
        base_topic_url = f"{topic_info.base_url}/t/topic/{topic_info.topic_id}"

        # 构建结果文本
        divider = "=" * 80 + "\n"
        result = [
            divider,
            f"{'LINUX DO 抽奖结果 - 0.0.5':^78}\n",
            divider,
            f"帖子链接: {base_topic_url}\n",
            f"帖子标题: {topic_info.title}\n",
            f"发帖时间: {created_time.strftime('%Y-%m-%d %H:%M:%S')}\n",
            "-" * 80 + "\n",
            f"抽奖时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"参与楼层: {valid_floors[0]} - {valid_floors[-1]} 楼\n",
            f"有效楼层: {total_floors} 楼\n",
            f"中奖数量: {winners_count} 个\n",
            f"最终种子: {final_seed}\n",
            "-" * 80 + "\n",
            "恭喜以下楼层中奖:\n",
            "-" * 80 + "\n"
        ]

        # 添加获奖楼层
        for i, floor in enumerate(winning_floors, 1):
            floor_url = topic_info.get_post_url(floor)
            result.append(f"[{i:^6}] {floor:>4} 楼，楼层链接: {floor_url}\n")

        result.extend([
            divider,
            "注: 楼层顺序即为抽奖顺序\n",
            divider
        ])

        return {"success": True, "result": "".join(result)}

    except LotteryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8000)
