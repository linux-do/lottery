# lottery
LINUX DO 抽奖脚本

1. 修改 `seed.txt` 文件内容，以便固定本次抽奖结果。我们可以将 `seed.txt` 放进加密 `zip` 压缩包中提前上传到抽奖帖中。
2. 直接 `python lottery.py -t` 启动交互模式。会要求输入：帖子地址、中奖人数。
3. 或者 `python lottery.py 帖子地址 中奖人数` 直接抽奖。
4. 如果需要登录的帖子，可以在 `cookies.txt` 中填入你的 cookies。可以F12在网络请求中找到 `Cookie` 头的内容直接复制进去。
5. 抽奖之前，需要先关闭帖子。
