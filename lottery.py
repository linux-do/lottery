import argparse
import hashlib
import random
import re
import sys
from datetime import datetime

import requests


class ForumTopicInfo:
    def __init__(self, topic_id, post_number=None):
        self.topic_id = topic_id
        self.post_number = post_number
        self.highest_post_number = None
        self.base_url = "https://linux.do"
        self.cookies = self._load_cookies()

    @classmethod
    def from_url(cls, url):
        """从URL中解析主题信息"""
        pattern = r"/t/topic/(\d+)(?:/(\d+))?"
        match = re.search(pattern, url)
        if not match:
            raise ValueError("无法从URL中解析出主题ID")

        topic_id = match.group(1)
        post_number = match.group(2)  # 可能为None
        return cls(topic_id, post_number)

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

    def fetch_highest_post_number(self):
        """获取主题的最高楼层数并检查帖子状态"""
        json_url = f"{self.base_url}/t/{self.topic_id}.json"
        try:
            response = requests.get(json_url, headers=self.cookies)
            response.raise_for_status()
            data = response.json()

            # 检查帖子是否已关闭或已存档
            if not (data.get('closed') or data.get('archived')):
                print("错误: 帖子尚未关闭或存档，不能进行抽奖")
                sys.exit(1)

            self.highest_post_number = data['highest_post_number']
            return self.highest_post_number
        except requests.RequestException as e:
            print(f"错误: 获取主题信息失败: {str(e)}")
            print("提示: 如果帖子需要登录，请确保cookies.txt文件存在且内容有效")
            sys.exit(1)
        except KeyError:
            print("错误: 返回的JSON数据格式不正确")
            sys.exit(1)

    def get_post_url(self, post_number):
        """获取特定楼层的URL"""
        return f"{self.base_url}/t/topic/{self.topic_id}/{post_number}"


def generate_final_seed(max_floor):
    """读取seed文件内容并与楼层数一起计算SHA256哈希值"""
    try:
        with open('seed.txt', 'rb') as f:
            content = f.read()
            if len(content) == 0:
                print("错误: seed.txt文件内容不能为空")
                sys.exit(1)
        final_content = content + str(max_floor).encode('utf-8')
        sha256_hash = hashlib.sha256(final_content).hexdigest()
        return sha256_hash
    except FileNotFoundError:
        print("错误: 在当前目录下找不到seed.txt文件")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 读取seed文件时发生错误: {str(e)}")
        sys.exit(1)


def generate_winning_floors(seed, max_floor, winners_count):
    """生成中奖楼层"""
    valid_floors_count = max_floor - 1
    if winners_count > valid_floors_count:
        print(f"错误: 中奖人数({winners_count})不能大于有效楼层数({valid_floors_count})")
        sys.exit(1)

    random.seed(seed)
    winning_floors = []
    available_floors = list(range(2, max_floor + 1))

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
    print("论坛抽奖程序 - 交互模式")
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

            return topic_url, int(winners_count)

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

    args = parser.parse_args()

    if args.terminal:
        topic_url, winners_count = get_interactive_input()
    else:
        if args.topic_url is None or args.winners_count is None:
            parser.print_help()
            sys.exit(1)
        topic_url = args.topic_url
        winners_count = args.winners_count

    try:
        topic_info = ForumTopicInfo.from_url(topic_url)
        max_floor = topic_info.fetch_highest_post_number()

        if max_floor < 2:
            print("错误: 帖子楼层数必须大于1")
            sys.exit(1)

        # 生成最终的seed并抽奖
        final_seed = generate_final_seed(max_floor)
        winning_floors = generate_winning_floors(final_seed, max_floor, winners_count)

        # 输出结果
        print_divider()
        print(f"{'LINUX DO 抽奖结果':^78}")
        print_divider()

        # 输出基本信息
        print(f"抽奖时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        base_topic_url = f"{topic_info.base_url}/t/topic/{topic_info.topic_id}"
        print(f"帖子链接: {base_topic_url}")
        print(f"参与楼层: 2 - {max_floor} 楼")
        print(f"总楼层数: {max_floor} 楼")
        print(f"有效楼层: {max_floor - 1} 楼 (不含主帖)")
        print(f"中奖数量: {winners_count} 个")
        print(f"最终种子: {final_seed}")

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
