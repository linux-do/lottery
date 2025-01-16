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
      <v-file-input
        v-model="seedFile"
        label="上传 seed 文件"
        accept=".txt"
      />
      <v-textarea
        v-model="seedContent"
        label="或输入 seed 内容"
        rows="3"
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
        {{ customServerEnabled ? "提交（自定义服务器）" : "提交" }}
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
            placeholder="http://localhost:5000"
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
    </v-expansion-panels>
  </v-container>
</template>

<script setup>
import { ref, watch } from "vue";
import axios from "axios";

const topicUrl = ref("");
const winnersCount = ref(1);
const useDrand = ref(false);
const seedFile = ref(null);
const seedContent = ref("");
const cookies = ref("");
const result = ref(null);
const error = ref("");
const loading = ref(false);
const customServer = ref(localStorage.getItem("customServer") || "");
const customServerEnabled = ref(!!customServer.value);

watch(customServer, (newVal) => {
  localStorage.setItem("customServer", newVal);
});

const submitForm = async () => {
  try {
    error.value = "";
    result.value = null;
    loading.value = true;

    let seed = seedContent.value;
    if (seedFile.value) {
      const file = seedFile.value;
      const reader = new FileReader();
      reader.onload = (e) => {
        seed = e.target.result;
        sendRequest(seed);
      };
      reader.readAsText(file);
    } else {
      sendRequest(seed);
    }
  } catch (err) {
    error.value = "提交表单时发生错误";
    console.error(err);
    loading.value = false;
  }
};

const sendRequest = async (seed) => {
  try {
    const serverUrl = customServerEnabled.value
      ? customServer.value
      : "http://localhost:5000";
    const response = await axios.post(`${serverUrl}/api`, {
      topic_url: topicUrl.value,
      winners_count: winnersCount.value,
      use_drand: useDrand.value,
      seed: seed,
      cookies: cookies.value,
    });
    result.value = response.data;
  } catch (err) {
    error.value = err.response?.data?.error || "请求失败";
  } finally {
    loading.value = false;
  }
};
</script>

<style>
.v-container {
  max-width: 600px;
  margin: 0 auto;
  padding-top: 20px;
}
</style>
