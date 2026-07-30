import createClient from "openapi-fetch";

import type { paths } from "./schema";

export const createApiClient = (baseUrl: string) =>
  createClient<paths>({
    baseUrl,
    credentials: "include"
  });

export const createChatStream = (
  baseUrl: string,
  body: { message: string; conversation_id: string },
  csrfToken: string
) =>
  fetch(`${baseUrl}/api/chat/stream/`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken
    },
    body: JSON.stringify(body)
  });

export type { components, paths } from "./schema";
