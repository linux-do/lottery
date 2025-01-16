# lottery
LINUX DO 抽奖脚本

1. 修改 `seed.txt` 文件内容，以便固定本次抽奖结果。我们可以将 `seed.txt` 放进加密 `zip` 压缩包中提前上传到抽奖帖中。
2. 直接 `python lottery.py -t` 启动交互模式。会要求输入：帖子地址、中奖人数。
3. 或者 `python lottery.py 帖子地址 中奖人数` 直接抽奖。
4. 如果需要登录的帖子，可以在 `cookies.txt` 中填入你的 cookies。可以F12在网络请求中找到 `Cookie` 头的内容直接复制进去。
5. 抽奖之前，需要先关闭帖子。

# Lottery API

## 概述

该API允许用户通过HTTP请求进行抽奖操作。用户可以传入帖子URL、中奖人数、是否使用云端随机数以及种子文件内容，API将返回抽奖结果。

## 接口文档

### POST /lottery

#### 请求参数

- `topic_url` (string): 帖子URL
- `winners_count` (integer): 中奖人数
- `use_drand` (boolean): 是否启用云端随机数
- `seed` (string): 种子文件内容（可选）

#### 请求示例

##### JSON格式

```json
{
  "topic_url": "https://linux.do/t/topic/12345",
  "winners_count": 3,
  "use_drand": true,
  "seed": "example_seed_content"
}
```

##### Form-Data格式

```
topic_url=https://linux.do/t/topic/12345
winners_count=3
use_drand=true
seed=example_seed_content
```

#### 响应参数

- `topic_url` (string): 帖子URL
- `title` (string): 帖子标题
- `created_at` (integer): 发帖时间（Unix时间戳）
- `last_posted_at` (integer): 最后回复时间（Unix时间戳）
- `highest_post_number` (integer): 最高楼层号
- `valid_post_numbers` (array): 有效楼层号数组
- `winners_count` (integer): 中奖人数
- `final_seed` (string): 最终种子
- `winning_floors` (array): 中奖楼层数组
- `drand_randomness` (string, optional): 云端随机数（如果启用）

#### 响应示例

```json
{
  "topic_url": "https://linux.do/t/topic/12345",
  "title": "Example Topic",
  "created_at": 1692803367,
  "last_posted_at": 1692806967,
  "highest_post_number": 100,
  "valid_post_numbers": [1, 2, 3, 4, 5],
  "winners_count": 3,
  "final_seed": "example_final_seed",
  "winning_floors": [2, 4, 5],
  "drand_randomness": "example_drand_randomness"
}
```

## 使用示例

### 使用curl发送JSON请求

```sh
curl -X POST http://localhost:3000/lottery \
     -H "Content-Type: application/json" \
     -d '{
           "topic_url": "https://linux.do/t/topic/12345",
           "winners_count": 3,
           "use_drand": true,
           "seed": "example_seed_content"
         }'
```

### 使用curl发送Form-Data请求

```sh
curl -X POST http://localhost:3000/lottery \
     -F "topic_url=https://linux.do/t/topic/12345" \
     -F "winners_count=3" \
     -F "use_drand=true" \
     -F "seed=example_seed_content"
```