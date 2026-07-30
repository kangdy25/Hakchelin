import { createApiClient } from "@hakchelin/api-client";

/**
 * Staging-only bridge client. Empty API base URLs intentionally preserve the
 * current Supabase adapter until each read flow is switched in a later PR.
 */
export const useDjangoApi = () => {
  const { public: config } = useRuntimeConfig();
  const supabase = useSupabaseClient();
  const enabled = computed(() => Boolean(config.apiBaseUrl));
  const getClient = async () => {
    const client = createApiClient(config.apiBaseUrl);
    const { data } = await supabase.auth.getSession();
    if (data.session?.access_token)
      client.use({ onRequest: ({ request }) => {
        request.headers.set("Authorization", `Bearer ${data.session?.access_token}`);
        return request;
      } });
    return client;
  };

  return { enabled, getClient };
};
