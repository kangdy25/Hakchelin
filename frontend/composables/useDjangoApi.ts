import { createApiClient } from "@hakchelin/api-client";

/**
 * Staging-only bridge client. Empty API base URLs intentionally preserve the
 * current Supabase adapter until each read flow is switched in a later PR.
 */
export const useDjangoApi = () => {
  const { public: config } = useRuntimeConfig();
  const enabled = computed(() => Boolean(config.apiBaseUrl));
  const client = computed(() => createApiClient(config.apiBaseUrl));

  return { enabled, client };
};
