<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

type ChatMessage = { role: "user" | "assistant"; content: string };

const { t } = useI18n({ useScope: "global" });
const api = useApi();
const { userId } = useUserProfile();

const isOpen = ref(false);
const loading = ref(false);
const loaded = ref(false);
const input = ref("");
const messages = ref<ChatMessage[]>([]);
const chatBody = ref<HTMLElement | null>(null);
const conversationId = ref("");
const submitAfterComposition = ref(false);

const storageKey = computed(() => (userId.value ? `hakchelin-chat-conversation-${userId.value}` : ""));

const makeConversationId = () => crypto.randomUUID();

const renderMarkdown = (content: string) => {
  const normalized = content
    .replace(/\r/g, "")
    // Gemini occasionally starts a Markdown list directly after a sentence.
    // Normalise it before rendering so "안내드립니다.- **항목**" remains readable.
    .replace(/(^|[^\n])[-*]\s+(?=\*\*)/g, (_match, prefix) => `${prefix}${prefix ? "\n" : ""}- `);
  const inline = (value: string) =>
    value
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");
  return normalized
    .split("\n")
    .map((line) => {
      if (!line.trim()) return '<div class="h-2"></div>';
      if (line.startsWith("- ")) return `<div class="chat-list-item">• ${inline(line.slice(2))}</div>`;
      return `<div>${inline(line)}</div>`;
    })
    .join("");
};

const scrollToBottom = async () => {
  await nextTick();
  if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight;
};

const initializeConversation = () => {
  if (!process.client || !storageKey.value) return;
  conversationId.value = localStorage.getItem(storageKey.value) || makeConversationId();
  localStorage.setItem(storageKey.value, conversationId.value);
};

const loadHistory = async () => {
  if (!userId.value || !conversationId.value || loaded.value) return;
  try {
    messages.value = await api.chat.getMessages(conversationId.value);
  } catch {
    messages.value = [];
  }
  loaded.value = true;
  await scrollToBottom();
};

const openChat = async () => {
  isOpen.value = true;
  initializeConversation();
  await loadHistory();
};

const resetConversation = () => {
  if (!storageKey.value) return;
  conversationId.value = makeConversationId();
  localStorage.setItem(storageKey.value, conversationId.value);
  messages.value = [];
  loaded.value = true;
};

const submitOnEnter = (event: KeyboardEvent) => {
  // Korean/Japanese IMEs use Enter to commit the final composing character.
  // Sending during that composition drops the last syllable from the message.
  if (event.isComposing || event.keyCode === 229) {
    submitAfterComposition.value = true;
    return;
  }
  event.preventDefault();
  void send();
};

const submitAfterCommittingComposition = async () => {
  if (!submitAfterComposition.value) return;
  submitAfterComposition.value = false;
  await nextTick();
  void send();
};

const send = async () => {
  const message = input.value.trim();
  if (!message || loading.value || message.length > 100 || !conversationId.value) return;
  // Lock before the first await. Otherwise two fast Enter/click events can both
  // pass the guard while getSession() is still pending.
  loading.value = true;

  try {
    messages.value.push({ role: "user", content: message });
    messages.value.push({ role: "assistant", content: "" });
    input.value = "";
    await scrollToBottom();

    const response = await api.chat.stream({ message, conversationId: conversationId.value });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.error || t("chat.errors.default"));
    }
    const reader = response.body?.getReader();
    if (!reader) throw new Error(t("chat.errors.default"));
    const decoder = new TextDecoder();
    let buffer = "";
    const processEvents = async (source: string) => {
      const events = source.split("\n\n");
      buffer = events.pop() || "";
      for (const event of events) {
        const type = event.match(/^event: (.+)$/m)?.[1];
        const raw = event.match(/^data: (.+)$/m)?.[1];
        if (!type || !raw) continue;
        const data = JSON.parse(raw);
        const assistant = messages.value[messages.value.length - 1];
        if (type === "token" && assistant?.role === "assistant") {
          assistant.content += String(data.text || "");
          await scrollToBottom();
        } else if (type === "done" && assistant?.role === "assistant" && typeof data.text === "string") {
          // Reconcile with the server's complete answer. This protects the last
          // token when a streamed SSE chunk is cut off at a network boundary.
          assistant.content = data.text;
          await scrollToBottom();
        } else if (type === "error") {
          throw new Error(data.message || t("chat.errors.default"));
        }
      }
    };
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      await processEvents(buffer);
    }
    // Flush a multibyte character held by TextDecoder and handle the final SSE
    // event even if a proxy closes the stream without its trailing delimiter.
    buffer += decoder.decode();
    if (buffer.trim()) await processEvents(`${buffer}\n\n`);
    const assistant = messages.value[messages.value.length - 1];
    if (assistant?.role === "assistant" && !assistant.content) assistant.content = t("chat.errors.empty");
  } catch (error) {
    const assistant = messages.value[messages.value.length - 1];
    if (assistant?.role === "assistant")
      assistant.content = error instanceof Error ? error.message : t("chat.errors.default");
  } finally {
    loading.value = false;
    await scrollToBottom();
  }
};

watch(userId, () => {
  loaded.value = false;
  messages.value = [];
  initializeConversation();
});
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-30" @click="isOpen = false" aria-hidden="true" />
  <div class="fixed bottom-24 right-4 z-40 md:bottom-7 md:right-7">
    <Transition name="chat-panel">
      <section
        v-if="isOpen"
        class="absolute bottom-16 right-0 flex h-[min(560px,70vh)] w-[min(380px,calc(100vw-2rem))] flex-col overflow-hidden rounded-3xl border border-green-100 bg-white shadow-2xl"
        @click.stop
      >
        <header class="flex items-center justify-between bg-[#2E7D32] px-5 py-4 text-white">
          <div>
            <h2 class="font-black">🍱 {{ t("chat.title") }}</h2>
            <p class="mt-0.5 text-[11px] text-green-100">{{ t("chat.subtitle") }}</p>
          </div>
          <div class="flex gap-1">
            <button
              @click="resetConversation"
              :title="t('chat.new_conversation')"
              class="rounded-lg px-2 py-1 text-sm hover:bg-white/15"
            >
              ↻
            </button>
            <button
              @click="isOpen = false"
              :title="t('chat.close')"
              class="rounded-lg px-2 py-1 text-lg hover:bg-white/15"
            >
              ×
            </button>
          </div>
        </header>

        <div ref="chatBody" class="flex-1 space-y-3 overflow-y-auto bg-[#F8FAF8] p-4">
          <div v-if="!messages.length" class="rounded-2xl bg-white p-4 text-sm leading-relaxed text-gray-600 shadow-sm">
            {{ t("chat.greeting") }}
          </div>
          <article
            v-for="(item, index) in messages"
            :key="index"
            class="flex"
            :class="item.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed"
              :class="
                item.role === 'user'
                  ? 'rounded-br-md bg-[#2E7D32] text-white whitespace-pre-wrap'
                  : 'rounded-bl-md bg-white text-gray-700 shadow-sm'
              "
            >
              <span v-if="item.content && item.role === 'user'">{{ item.content }}</span>
              <div v-else-if="item.content" class="chat-markdown" v-html="renderMarkdown(item.content)" />
              <span v-else-if="loading" class="inline-flex gap-1"
                ><i class="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" /><i
                  class="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" /><i
                  class="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]"
              /></span>
            </div>
          </article>
        </div>

        <form @submit.prevent="send" class="border-t border-gray-100 bg-white p-3">
          <div
            class="flex items-end gap-2 rounded-2xl border border-gray-200 bg-gray-50 px-3 py-2 focus-within:border-[#2E7D32]"
          >
            <textarea
              v-model="input"
              :disabled="loading"
              :maxlength="100"
              rows="1"
              :placeholder="t('chat.placeholder')"
              class="max-h-24 flex-1 resize-none bg-transparent text-sm outline-none"
              @compositionend="submitAfterCommittingComposition"
              @keydown.enter.exact="submitOnEnter"
            />
            <button
              :disabled="loading || !input.trim()"
              class="rounded-xl bg-[#2E7D32] px-3 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-40"
            >
              ↑
            </button>
          </div>
          <p class="mt-1 text-right text-[10px] text-gray-400">{{ input.length }}/100</p>
        </form>
      </section>
    </Transition>

    <button
      @click="isOpen ? (isOpen = false) : openChat()"
      class="flex h-14 w-14 items-center justify-center rounded-full bg-[#2E7D32] text-2xl text-white shadow-lg shadow-green-700/30 transition hover:scale-105"
      :aria-label="t('chat.title')"
    >
      💬
    </button>
  </div>
</template>

<style scoped>
.chat-panel-enter-active,
.chat-panel-leave-active {
  transition: all 0.2s ease;
}
.chat-panel-enter-from,
.chat-panel-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.97);
}
.chat-markdown :deep(strong) {
  font-weight: 800;
}
.chat-markdown :deep(code) {
  border-radius: 0.25rem;
  background: #f3f4f6;
  padding: 0.1rem 0.25rem;
  font-size: 0.8em;
}
.chat-list-item {
  padding-left: 0.15rem;
}
</style>
