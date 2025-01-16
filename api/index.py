import hashlib
import random
import re
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

import dateutil
import requests
from dotenv import load_dotenv
import os

load_dotenv()

DRAND_HASH = os.getenv('DRAND_HASH', '52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971')
DRAND_PERIOD = int(os.getenv('DRAND_PERIOD', 3))
DRAND_GENESIS_TIME = int(os.getenv('DRAND_GENESIS_TIME', 1692803367))
BASE_URL = os.getenv('BASE_URL', 'https://linux.do')
CONNECT_URL = os.getenv('CONNECT_URL', 'https://connect.linux.do')
DRAND_SERVER = os.getenv('DRAND_SERVER', 'https://drand.cloudflare.com')

app = Flask(__name__)
CORS(app)

DRAND_INFO = {
    "period": DRAND_PERIOD,
    "genesis_time": DRAND_GENESIS_TIME,
    "hash": DRAND_HASH,
}

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
    def __init__(self, topic_id, cookies=None):
        self.topic_id = topic_id
        self.created_by = None
        self.title = None
        self.highest_post_number = None
        self.created_at = None
        self.last_posted_at = None
        self.base_url = BASE_URL
        self.connect_url = CONNECT_URL
        self.cookies = cookies
        self.valid_post_ids = []
        self.valid_post_numbers = []
        self.valid_post_created = []

    @classmethod
    def from_url(cls, url, cookies=None):
        """从URL中解析主题信息"""
        pattern = r"/t/topic/(\d+)(?:/\d+)?"
        match = re.search(pattern, url)
        if not match:
            raise ValidationError("无法从URL中解析出主题ID")

        return cls(match.group(1), cookies)

    def fetch_topic_info(self):
        """获取主题信息"""
        json_url = f"{self.base_url}/t/{self.topic_id}.json"
        try:
            response = requests.get(json_url, headers={'Cookie': self.cookies})
            response.raise_for_status()
            data = response.json()

            # 检查帖子是否已关闭或已存档
            if not (data.get('closed') or data.get('archived')):
                raise ValidationError("帖子尚未关闭或存档，不能进行抽奖")

            self.title = data['title']
            self.highest_post_number = data['highest_post_number']
            self.created_at = data['created_at']
            self.last_posted_at = data['last_posted_at']
            self.created_by = data['details']['created_by']['username']

        except requests.RequestException as e:
            raise TopicError(f"获取主题信息失败: {str(e)}\n如果帖子需要登录，请确保cookies.txt文件存在且内容有效")
        except KeyError:
            raise TopicError("返回的JSON数据格式不正确")

    def fetch_valid_post_numbers(self, last_floor=None):
        """获取有效的楼层号"""
        valid_posts_url = f"{self.connect_url}/api/topic/{self.topic_id}/valid_post_number"
        try:
            response = requests.get(valid_posts_url, headers={'Cookie': self.cookies})
            response.raise_for_status()
            data = response.json()

            self.valid_post_numbers = data.get('rows', [])
            self.valid_post_ids = data.get('ids', [])
            self.valid_post_created = data.get('created', [])

            if not self.valid_post_numbers or not self.valid_post_ids or not self.valid_post_created:
                raise ValidationError("该帖不符合抽奖条件（如：版块错误、帖子未关闭等）")

            if last_floor is not None:
                cut_index = next((i for i, floor in enumerate(self.valid_post_numbers) if floor > last_floor),
                                 len(self.valid_post_numbers))

                self.valid_post_numbers = self.valid_post_numbers[:cut_index]
                self.valid_post_ids = self.valid_post_ids[:cut_index]
                self.valid_post_created = self.valid_post_created[:cut_index]

            return self.valid_post_numbers
        except requests.RequestException as e:
            raise TopicError(f"获取有效楼层失败: {str(e)}")
        except (KeyError, ValueError):
            raise TopicError("返回的有效楼层数据格式不正确")

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

def generate_final_seed(topic_info, winners_count, use_drand, last_posted_at):
    """获取帖子信息一起计算多重哈希值"""
    try:
        seed_content = '|'.join([
            str(winners_count),
            str(topic_info.topic_id),
            str(topic_info.created_by),
            str(topic_info.created_at),
            ','.join([str(i) for i in topic_info.valid_post_ids]),
            ','.join([str(i) for i in topic_info.valid_post_numbers]),
            ','.join(topic_info.valid_post_created),
        ]).encode('utf-8')

        md5_hash = hashlib.md5(seed_content).hexdigest()
        sha1_hash = hashlib.sha1(seed_content).hexdigest()
        sha512_hash = hashlib.sha512(seed_content).hexdigest()
        combined = (md5_hash + sha1_hash + sha512_hash).encode('utf-8')

        if use_drand:
            drand_randomness, drand_round = fetch_drand_randomness(last_posted_at)
            combined += f"|{drand_randomness}|{drand_round}".encode('utf-8')

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

@app.route('/api', methods=['POST'])
def lottery():
    try:
        print("Received POST request")
        if request.content_type == 'application/json':
            data = request.json
            print("Processing JSON data")
        elif request.content_type.startswith('multipart/form-data'):
            data = request.form.to_dict()
            for key in data:
                if isinstance(data[key], list):
                    data[key] = data[key][0]
            print("Processing form-data")
        else:
            print("Unsupported Content-Type")
            return jsonify({'error': 'Unsupported Content-Type'}), 400

        topic_url = data.get('topic_url')
        winners_count = data.get('winners_count')
        if winners_count:
            winners_count = int(winners_count)
        else:
            print("Missing parameter: winners_count")
            raise ValidationError("缺少必要的参数: winners_count")

        last_floor = data.get('last_floor')
        if last_floor:
            last_floor = int(last_floor)
        else:
            last_floor = None

        use_drand = str(data.get('use_drand', 'false')).lower() in ['true', '1', 'yes', 'y']
        cookies = data.get('cookies', '')

        if not topic_url or not winners_count:
            print("Missing necessary parameters")
            raise ValidationError("缺少必要的参数")

        print(f"Processing lottery for topic URL: {topic_url} with {winners_count} winners")

        topic_info = ForumTopicInfo.from_url(topic_url, cookies)
        topic_info.fetch_topic_info()
        valid_floors = topic_info.fetch_valid_post_numbers(last_floor)

        if len(valid_floors) < 2:
            print("Not enough valid floors")
            raise ValidationError("没有足够的参与楼层")

        last_posted_at = topic_info.valid_post_created[-1]
        final_seed = generate_final_seed(topic_info, winners_count, use_drand, last_posted_at)
        winning_floors = generate_winning_floors(final_seed, valid_floors, winners_count)

        response = {
            'topic_url': topic_url,
            'title': topic_info.title,
            'created_at': int(dateutil.parser.parse(topic_info.created_at).timestamp()),
            'last_posted_at': int(dateutil.parser.parse(topic_info.last_posted_at).timestamp()),
            'highest_post_number': topic_info.highest_post_number,
            'valid_post_numbers': valid_floors,
            'winners_count': winners_count,
            'final_seed': final_seed,
            'winning_floors': winning_floors,
            'drand_randomness': fetch_drand_randomness(last_posted_at) if use_drand else None
        }

        print("Lottery processed successfully")
        return jsonify(response), 200

    except LotteryError as e:
        print(f"Lottery error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Server error: {str(e)}")
        return jsonify({'error': '服务器内部错误'}), 500

print(f"Loaded DRAND_INFO: {DRAND_INFO}")

if __name__ == '__main__':
    print("Starting server")
    app.run(host='0.0.0.0', port=5000, debug=True)

