# lottery
LINUX DO 抽奖脚本

1. 安装依赖：`pip install -r requirements.txt`
2. 直接 `python lottery.py -t` 启动交互模式。会要求输入：帖子地址、中奖人数、最后楼层（可选）。
3. 或者 `python lottery.py 帖子地址 中奖人数 -f 最后楼层（可选）` 直接抽奖。
4. 如果需要登录的帖子，可以在 `cookies.txt` 中填入你的 cookies。可以F12在网络请求中找到 `Cookie` 头的内容直接复制进去。
5. 帖子需要发在 `福利羊毛` 相关版块。抽奖之前，需要先关闭帖子。

LINUX DO 抽奖服务
1. 安装依赖：`pip install -r requirements.txt`
2. `python lottery_service.py` 启动服务。
3. 浏览器打开 `http://127.0.0.1:8000`，输入帖子地址、中奖人数、最后楼层（可选）进行抽奖。
