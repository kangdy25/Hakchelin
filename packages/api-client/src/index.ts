import createClient from "openapi-fetch";

import type { paths } from "./schema";

export const createApiClient = (baseUrl: string) =>
  createClient<paths>({
    baseUrl,
    credentials: "include"
  });

export type { paths } from "./schema";
