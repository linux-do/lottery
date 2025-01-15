import argparse
import hashlib
import random
import re
import sys
from datetime import datetime

import dateutil
import requests

DRAND_INFO = {
    "period": 3,
    "genesis_time": 1692803367,
    "hash": "52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971",
}

class ForumTopicInfo:
    def __init__(self, topic_id):
        self.topic_id = topic_id
        self.title = None
        self.highest_post_number = None
        self.created_at = None
        self.last_posted_at = None
        self.base_url = "https://linux.do"
        self.connect_url = "https://connect.linux.do"
        self.cookies = self._load_cookies()
        self.valid_post_numbers = []

    @classmethod
    def from_url(cls, url):
        """从URL中解析主题信息"""
        pattern = r"/t/topic/(\d+)(?:/\d+)?"
        match = re.search(pattern, url)
        if not match:
            raise ValueError("无法从URL中解析出主题ID")

        return cls(match.group(1))

    @staticmethod
    def _load_cookies():
        """读取cookies文件"""
        try:
            with open('cookies.txt', 'r') as f:
                content = f.read()
                if len(content) > 0:
                    return {'Cookie': content.strip()}

                return {}
        except FileNotFoundError:
            return {}

    def fetch_topic_info(self):
        """获取主题信息"""
        json_url = f"{self.base_url}/t/{self.topic_id}.json"
        try:
            response = requests.get(json_url, headers=self.cookies)
            response.raise_for_status()
            data = response.json()

            # 检查帖子是否已关闭或已存档
            if not (data.get('closed') or data.get('archived')):
                print("错误: 帖子尚未关闭或存档，不能进行抽奖")
                sys.exit(1)

            if data.get('category_id') not in [36, 60, 61, 62]:
                print("错误: 帖子不在指定分类下，不能进行抽奖")
                sys.exit(1)

            self.title = data['title']
            self.highest_post_number = data['highest_post_number']
            self.created_at = data['created_at']
            self.last_posted_at = data['last_posted_at']

        except requests.RequestException as e:
            print(f"错误: 获取主题信息失败: {str(e)}")
            print("提示: 如果帖子需要登录，请确保cookies.txt文件存在且内容有效")
            sys.exit(1)
        except KeyError:
            print("错误: 返回的JSON数据格式不正确")
            sys.exit(1)

    def fetch_valid_post_numbers(self):
        """获取有效的楼层号"""
        valid_posts_url = f"{self.connect_url}/api/topic/{self.topic_id}/valid_post_number"
        try:
            response = requests.get(valid_posts_url, headers=self.cookies)
            response.raise_for_status()
            data = response.json()

            self.valid_post_numbers = data.get('rows', [])
            if not self.valid_post_numbers:
                print("错误: 没有找到有效的楼层")
                sys.exit(1)

            return self.valid_post_numbers
        except requests.RequestException as e:
            print(f"错误: 获取有效楼层失败: {str(e)}")
            sys.exit(1)
        except (KeyError, ValueError):
            print("错误: 返回的有效楼层数据格式不正确")
            sys.exit(1)

    def get_post_url(self, post_number):
        """获取特定楼层的URL"""
        return f"{self.base_url}/t/topic/{self.topic_id}/{post_number}"


def fetch_drand_randomness(last_posted_at):
    """获取drand随机数"""
    timestamp = int(dateutil.parser.parse(last_posted_at).timestamp())
    round_number = (timestamp - DRAND_INFO['genesis_time']) // DRAND_INFO['period']
    if round_number < 0:
        print("错误: 计算的drand轮次无效")
        sys.exit(1)
    drand_url = f"https://api.drand.sh/{DRAND_INFO['hash']}/public/{round_number}"
    try:
        response = requests.get(drand_url)
        response.raise_for_status()
        data = response.json()
        return data['randomness'], data['round']
    except requests.RequestException as e:
        print(f"错误: 获取云端随机数失败: {str(e)}")
        sys.exit(1)


def generate_final_seed(topic_info, winners_count, use_drand):
    """读取seed文件内容并与其他信息一起计算多重哈希值"""
    try:
        with open('seed.txt', 'rb') as f:
            content = f.read()
            if len(content) == 0:
                print("错误: seed.txt文件内容不能为空")
                sys.exit(1)

        md5_hash = hashlib.md5(content).hexdigest()
        sha1_hash = hashlib.sha1(content).hexdigest()
        sha512_hash = hashlib.sha512(content).hexdigest()
        combined = '|'.join([
            md5_hash, sha1_hash, sha512_hash,
            str(winners_count),
            str(topic_info.highest_post_number),
            str(topic_info.topic_id),
            str(topic_info.created_at),
            str(topic_info.last_posted_at)
        ])

        if use_drand:
            drand_randomness, drand_round = fetch_drand_randomness(topic_info.last_posted_at)
            combined += f"|{drand_randomness}|{drand_round}"

        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    except FileNotFoundError:
        print("错误: 在当前目录下找不到seed.txt文件")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取seed文件时发生错误: {str(e)}")
        sys.exit(1)


def generate_winning_floors(seed, valid_floors, winners_count):
    """生成中奖楼层"""
    total_floors = len(valid_floors)
    if winners_count > total_floors:
        print(f"错误: 中奖人数({winners_count})不能大于有效楼层数({total_floors})")
        sys.exit(1)

    random.seed(seed)
    winning_floors = []
    available_floors = valid_floors.copy()

    for _ in range(winners_count):
        winner = random.choice(available_floors)
        available_floors.remove(winner)
        winning_floors.append(winner)

    return winning_floors


def print_divider(char='=', width=80):
    """打印分隔线"""
    print(char * width)


def get_interactive_input():
    """交互式获取用户输入"""
    print_divider()
    print("LINUX DO 抽奖程序 - 交互模式")
    print_divider()

    while True:
        try:
            topic_url = input("\n请输入帖子URL: ")
            if not topic_url:
                print("错误: URL不能为空")
                continue

            winners_count = input("请输入中奖人数: ")
            if not winners_count.isdigit() or int(winners_count) < 1:
                print("错误: 中奖人数必须为大于0的整数")
                continue

            use_drand = input("是否启用云端随机数? (y/n) [n]: ").strip().lower()
            if use_drand in ['y', 'yes', 'true', '1', 'on']:
                use_drand = True
            else:
                use_drand = False
                print("云端随机数已禁用")


            return topic_url, int(winners_count), use_drand

        except KeyboardInterrupt:
            print("\n已取消操作")
            sys.exit(0)
        except Exception as e:
            print(f"错误: {str(e)}")
            continue


def main():
    parser = argparse.ArgumentParser(description='论坛抽奖脚本')
    parser.add_argument('-t', '--terminal', action='store_true', help='启用终端交互模式')
    parser.add_argument('topic_url', nargs='?', help='帖子URL')
    parser.add_argument('winners_count', nargs='?', type=int, help='中奖人数')
    parser.add_argument('--use-drand', action='store_true', help='启用云端随机数')

    args = parser.parse_args()

    if args.terminal:
        topic_url, winners_count, use_drand = get_interactive_input()
    else:
        if args.topic_url is None or args.winners_count is None:
            parser.print_help()
            sys.exit(1)
        topic_url = args.topic_url
        winners_count = args.winners_count
        use_drand = args.use_drand

    try:
        topic_info = ForumTopicInfo.from_url(topic_url)
        topic_info.fetch_topic_info()
        valid_floors = topic_info.fetch_valid_post_numbers()

        if len(valid_floors) < 2:
            print("错误: 没有足够的参与楼层")
            sys.exit(1)

        # 生成最终的seed并抽奖
        final_seed = generate_final_seed(topic_info, winners_count, use_drand)
        winning_floors = generate_winning_floors(final_seed, valid_floors, winners_count)

        # 输出结果
        print_divider()
        print(f"{'LINUX DO 抽奖结果 - 0.0.3':^78}")
        print_divider()

        # 输出基本信息
        created_time = dateutil.parser.parse(topic_info.created_at).astimezone()
        last_posted_time = dateutil.parser.parse(topic_info.last_posted_at).astimezone()
        base_topic_url = f"{topic_info.base_url}/t/topic/{topic_info.topic_id}"
        print(f"帖子链接: {base_topic_url}")
        print(f"帖子标题: {topic_info.title}")
        print(f"发帖时间: {created_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"最后回复: {last_posted_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print_divider('-')
        print(f"抽奖时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"参与楼层: {valid_floors[0]} - {valid_floors[-1]} 楼")
        print(f"总楼层数: {topic_info.highest_post_number} 楼")
        print(f"有效楼层: {len(valid_floors)} 楼")
        print(f"中奖数量: {winners_count} 个")
        print(f"最终种子: {final_seed}")

        if use_drand:
            drand_randomness, drand_round = fetch_drand_randomness(topic_info.last_posted_at)
            print(f"云端随机数: https://drand.cloudflare.com/{DRAND_INFO['hash']}/public/{drand_round}")

        # 输出中奖楼层
        print_divider('-')
        print(f"恭喜以下楼层中奖:")
        print_divider('-')
        for i, floor in enumerate(winning_floors, 1):
            floor_url = topic_info.get_post_url(floor)
            print(f"[{i:^6}] {floor:>4} 楼，楼层链接: {floor_url}")

        print_divider()
        print("注: 楼层顺序即为抽奖顺序")
        print_divider()

    except ValueError as e:
        print(f"错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
