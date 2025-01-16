import argparse
import hashlib
import random
import re
import sys
from datetime import datetime

import dateutil
import requests


class LotteryError(Exception):
    """抽奖过程中的基础异常类"""
    pass


class TopicError(LotteryError):
    """主题相关的异常"""
    pass


class ValidationError(LotteryError):
    """数据验证相关的异常"""
    pass


class FileError(LotteryError):
    """文件操作相关的异常"""
    pass


class ForumTopicInfo:
    def __init__(self, topic_id):
        self.topic_id = topic_id
        self.title = None
        self.created_at = None
        self.base_url = "https://linux.do"
        self.connect_url = "https://connect.linux.do"
        self.cookies = self._load_cookies()
        self.valid_post_ids = []
        self.valid_post_numbers = []
        self.valid_post_created = []

    @classmethod
    def from_url(cls, url):
        """从URL中解析主题信息"""
        pattern = r"/t/topic/(\d+)(?:/\d+)?"
        match = re.search(pattern, url)
        if not match:
            raise ValidationError("无法从URL中解析出主题ID")

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
                raise ValidationError("帖子尚未关闭或存档，不能进行抽奖")

            if data.get('category_id') not in [36, 60, 61, 62]:
                raise ValidationError("帖子不在指定分类下，不能进行抽奖")

            self.title = data['title']
            self.created_at = data['created_at']

        except requests.RequestException as e:
            raise TopicError(f"获取主题信息失败: {str(e)}\n如果帖子需要登录，请确保cookies.txt文件存在且内容有效")
        except KeyError:
            raise TopicError("返回的JSON数据格式不正确")

    def fetch_valid_post_numbers(self):
        """获取有效的楼层号"""
        valid_posts_url = f"{self.connect_url}/api/topic/{self.topic_id}/valid_post_number"
        try:
            response = requests.get(valid_posts_url, headers=self.cookies)
            response.raise_for_status()
            data = response.json()

            self.valid_post_numbers = data.get('rows', [])
            if not self.valid_post_numbers:
                raise ValidationError("没有找到有效的楼层")

            self.valid_post_ids = data.get('ids', [])
            if not self.valid_post_ids:
                raise ValidationError("没有找到有效的楼层")

            self.valid_post_created = data.get('created', [])
            if not self.valid_post_created:
                raise ValidationError("没有找到有效的楼层")

            return self.valid_post_numbers
        except requests.RequestException as e:
            raise TopicError(f"获取有效楼层失败: {str(e)}")
        except (KeyError, ValueError):
            raise TopicError("返回的有效楼层数据格式不正确")

    def get_post_url(self, post_number):
        """获取特定楼层的URL"""
        return f"{self.base_url}/t/topic/{self.topic_id}/{post_number}"


def generate_final_seed(topic_info, winners_count):
    """获取帖子信息一起计算多重哈希值"""
    try:
        seed_content = '|'.join([
            str(winners_count),
            str(topic_info.topic_id),
            str(topic_info.created_at),
            ','.join([str(i) for i in topic_info.valid_post_ids]),
            ','.join([str(i) for i in topic_info.valid_post_numbers]),
            ','.join(topic_info.valid_post_created),
        ]).encode('utf-8')

        md5_hash = hashlib.md5(seed_content).hexdigest()
        sha1_hash = hashlib.sha1(seed_content).hexdigest()
        sha512_hash = hashlib.sha512(seed_content).hexdigest()
        combined = (md5_hash + sha1_hash + sha512_hash).encode('utf-8')

        return hashlib.sha256(combined).hexdigest()
    except Exception as e:
        raise FileError(f"生成seed时发生错误: {str(e)}")


def generate_winning_floors(seed, valid_floors, winners_count):
    """生成中奖楼层"""
    total_floors = len(valid_floors)
    if winners_count > total_floors:
        raise ValidationError(f"中奖人数({winners_count})不能大于有效楼层数({total_floors})")

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
        topic_info.fetch_topic_info()
        valid_floors = topic_info.fetch_valid_post_numbers()

        if len(valid_floors) < 2:
            print("错误: 没有足够的参与楼层")
            sys.exit(1)

        # 生成最终的seed并抽奖
        final_seed = generate_final_seed(topic_info, winners_count)
        winning_floors = generate_winning_floors(final_seed, valid_floors, winners_count)

        # 输出结果
        print_divider()
        print(f"{'LINUX DO 抽奖结果 - 0.0.5':^78}")
        print_divider()

        # 输出基本信息
        created_time = dateutil.parser.parse(topic_info.created_at).astimezone()
        base_topic_url = f"{topic_info.base_url}/t/topic/{topic_info.topic_id}"
        print(f"帖子链接: {base_topic_url}")
        print(f"帖子标题: {topic_info.title}")
        print(f"发帖时间: {created_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print_divider('-')
        print(f"抽奖时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"参与楼层: {valid_floors[0]} - {valid_floors[-1]} 楼")
        print(f"有效楼层: {len(valid_floors)} 楼")
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

    except LotteryError as e:
        print(f"错误: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
