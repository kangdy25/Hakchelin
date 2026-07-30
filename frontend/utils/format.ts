export const formatPoints = (value: number | null | undefined, locale = "ko") =>
  new Intl.NumberFormat(locale === "ko" ? "ko-KR" : "en-US").format(value ?? 0);
