import { createApiClient, createChatStream } from "@hakchelin/api-client";

const readCookie = (name: string) => {
  if (!import.meta.client) return "";
  const prefix = `${encodeURIComponent(name)}=`;
  return (
    document.cookie
      .split("; ")
      .find((cookie) => cookie.startsWith(prefix))
      ?.slice(prefix.length) || ""
  );
};

export const useDjangoApi = () => {
  const { public: config } = useRuntimeConfig();
  const baseUrl = String(config.apiBaseUrl || "");
  const serverCookie = import.meta.server ? useRequestHeaders(["cookie"]).cookie : undefined;

  const getClient = () => {
    const client = createApiClient(baseUrl);
    client.use({
      onRequest: ({ request }) => {
        if (serverCookie) request.headers.set("Cookie", serverCookie);
        if (!["GET", "HEAD", "OPTIONS"].includes(request.method)) {
          const csrfToken = readCookie("csrftoken");
          if (csrfToken) request.headers.set("X-CSRFToken", decodeURIComponent(csrfToken));
        }
        return request;
      }
    });
    return client;
  };

  const ensureCsrf = async () => {
    if (readCookie("csrftoken")) return;
    const { error } = await getClient().GET("/api/auth/csrf/");
    if (error) throw error;
  };

  const streamChat = async (body: { message: string; conversation_id: string }) => {
    await ensureCsrf();
    return createChatStream(baseUrl, body, decodeURIComponent(readCookie("csrftoken")));
  };

  return { baseUrl, getClient, ensureCsrf, streamChat };
};
