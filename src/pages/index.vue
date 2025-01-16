<template>
  <v-container>
    <v-form @submit.prevent="submitForm">
      <v-text-field
        v-model="topicUrl"
        label="主题链接"
        required
      />
      <v-text-field
        v-model="winnersCount"
        label="抽中者数量"
        type="number"
        required
      />
      <v-text-field
        v-model="lastFloor"
        label="最后参与抽奖的楼层"
        type="number"
      />
      <v-textarea
        v-model="cookies"
        label="Cookies (可选)"
        rows="3"
      />
      <v-btn
        type="submit"
        :color="customServerEnabled === true ? 'red' : 'primary'"
      >
        {{
          customServerEnabled
            ? useDrand
              ? "提交（自定义服务器）（使用云端随机数）"
              : "提交（自定义服务器）"
            : useDrand
              ? "提交（云端随机数）"
              : "提交"
        }}
      </v-btn>&nbsp;&nbsp;
      <v-btn
        variant="text"
        @click="copyConfig"
      >
        复制以分享
      </v-btn>
    </v-form>
    <v-divider class="my-4" />
    <v-progress-linear
      v-if="loading"
      indeterminate
      color="primary"
    />
    <v-alert
      v-if="error"
      type="error"
    >
      {{ error }}
    </v-alert>
    <v-card v-if="result">
      <v-card-title>抽奖结果</v-card-title>
      <v-card-text>
        <p>
          主题链接:
          <a
            :href="result.topic_url"
            target="_blank"
          >{{ result.topic_url }}</a>
        </p>
        <p>标题: {{ result.title }}</p>
        <p>
          创建时间: {{ new Date(result.created_at * 1000).toLocaleString() }}
        </p>
        <p>
          最后回复时间:
          {{ new Date(result.last_posted_at * 1000).toLocaleString() }}
        </p>
        <p>最高楼层号: {{ result.highest_post_number }}</p>
        <p>有效楼层号: {{ result.valid_post_numbers.join(", ") }}</p>
        <p>抽中者数量: {{ result.winners_count }}</p>
        <p>最终种子: {{ result.final_seed }}</p>
        <p v-if="result.drand_randomness">
          云端随机数: {{ result.drand_randomness[0] }}
        </p>
        <p v-if="result.drand_randomness">
          云端随机轮次: {{ result.drand_randomness[1] }}
        </p>
        <v-card
          v-for="floor in result.winning_floors"
          :key="floor"
          class="my-2"
          :href="`${result.topic_url}/${floor}`"
          target="_blank"
          rel="noopener noreferrer"
          append-icon="mdi-open-in-new"
          :title="`楼层 ${floor}`"
        >
          <v-card-text>{{ floor }}</v-card-text>
        </v-card>
      </v-card-text>
    </v-card><br>
    <v-expansion-panels>
      <v-expansion-panel title="高级选项">
        <v-expansion-panel-text>
          <v-text-field
            v-model="customServer"
            label="自定义服务器"
            placeholder="/api"
            :disabled="!customServerEnabled"
          />
          <v-checkbox
            v-model="customServerEnabled"
            label="启用自定义服务器"
          />
          <v-checkbox
            v-model="useDrand"
            label="开启云端随机数"
          />
        </v-expansion-panel-text>
      </v-expansion-panel>
      <v-expansion-panel title="详细抽奖结果" v-if="result">
        <v-expansion-panel-text>
          <v-textarea
            class="mt-2"
            readonly
            rows="20"
            :value="`
================================================================================
                            LINUX DO 抽奖结果 - 0.0.5
================================================================================
帖子链接: ${result.topic_url}
帖子标题: ${result.title}
发帖时间: ${new Date(result.created_at * 1000).toLocaleString()}
--------------------------------------------------------------------------------
抽奖时间: ${new Date().toLocaleString()}
参与楼层: ${result.valid_post_numbers[0]} - ${result.valid_post_numbers[result.valid_post_numbers.length - 1]} 楼
有效楼层: ${result.valid_post_numbers.length} 楼
中奖数量: ${result.winners_count} 个
最终种子: ${result.final_seed}
${result.drand_randomness ? `云端随机数: ${result.drand_randomness[0]}
云端随机轮次: ${result.drand_randomness[1]}` : ''}
--------------------------------------------------------------------------------
恭喜以下楼层中奖:
--------------------------------------------------------------------------------
${result.winning_floors.map((floor, index) => `[  ${index + 1}   ]    ${floor} 楼，楼层链接: ${`${result.topic_url}/${floor}`} \n`).join('')}
================================================================================
注: 楼层顺序即为抽奖顺序
================================================================================
`"
          />
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-container>
</template>

<script setup>
import { ref, watch, onMounted } from "vue";
import axios from "axios";
import { useRoute } from "vue-router";

const route = useRoute();

const topicUrl = ref("");
const winnersCount = ref(1);
const lastFloor = ref(null);
const useDrand = ref(false);
const cookies = ref("");
const result = ref(null);
const error = ref("");
const loading = ref(false);
const customServer = ref(localStorage.getItem("customServer") || "");
const customServerEnabled = ref(!!customServer.value);

watch(customServer, (newVal) => {
  localStorage.setItem("customServer", newVal);
});

watch(customServerEnabled, (newVal) => {
  if (!newVal) {
    localStorage.removeItem("customServer");
  }
});

onMounted(() => {
  const query = route.query;
  if (query.topic_url) topicUrl.value = query.topic_url;
  if (query.winners_count) winnersCount.value = parseInt(query.winners_count);
  if (query.use_drand) useDrand.value = query.use_drand === "true";
  if (query.cookies) cookies.value = query.cookies;
  if (query.custom_server) {
    customServer.value = query.custom_server_url;
    customServerEnabled.value = true;
  }
  if (query.last_floor) lastFloor.value = parseInt(query.last_floor);
});

const submitForm = async () => {
  try {
    error.value = "";
    result.value = null;
    loading.value = true;

    sendRequest();
  } catch (err) {
    error.value = "提交表单时发生错误";
    console.error(err);
    loading.value = false;
  }
};

const sendRequest = async () => {
  try {
    const serverUrl = customServerEnabled.value
      ? customServer.value
      : "/api";
    const response = await axios.post(`${serverUrl}`, {
      topic_url: topicUrl.value,
      winners_count: winnersCount.value,
      last_floor: lastFloor.value,
      use_drand: useDrand.value,
      cookies: cookies.value,
    });
    result.value = response.data;
  } catch (err) {
    error.value = err.response?.data?.error || "请求失败";
  } finally {
    loading.value = false;
  }
};

const copyConfig = () => {
  const query = {
    topic_url: topicUrl.value,
    winners_count: winnersCount.value,
    use_drand: useDrand.value,
    cookies: cookies.value,
    last_floor: lastFloor.value,
  };
  if (customServerEnabled.value) {
    query.custom_server = true;
    query.custom_server_url = customServer.value;
  }
  const queryString = new URLSearchParams(query).toString();
  const url = `${window.location.origin}${window.location.pathname}?${queryString}`;
  navigator.clipboard.writeText(url).then(() => {
    alert("配置已复制到剪贴板");
  });
};
</script>

<style>
.v-container {
  max-width: 600px;
  margin: 0 auto;
  padding-top: 20px;
}
</style>
