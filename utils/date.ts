const KST_TIME_ZONE = "Asia/Seoul";

const dateParts = (value: Date | string, locale = "en-CA") => {
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat(locale, {
    timeZone: KST_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23"
  })
    .formatToParts(date)
    .reduce<Record<string, string>>((parts, part) => {
      if (part.type !== "literal") parts[part.type] = part.value;
      return parts;
    }, {});
};

export const getKstDateString = (value = new Date()) => {
  const { year, month, day } = dateParts(value);
  return `${year}-${month}-${day}`;
};

export const toKstDateTimeLocal = (value: string | null | undefined) => {
  if (!value) return "";
  const { year, month, day, hour, minute } = dateParts(value);
  return `${year}-${month}-${day}T${hour}:${minute}`;
};

export const formatDateTime = (value: string | null | undefined, locale: string) => {
  if (!value) return "-";
  return new Intl.DateTimeFormat(locale === "ko" ? "ko-KR" : "en-US", {
    timeZone: KST_TIME_ZONE,
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
};

export const formatMealDate = (value: string, locale: string) =>
  new Intl.DateTimeFormat(locale === "ko" ? "ko-KR" : "en-US", {
    timeZone: KST_TIME_ZONE,
    year: "numeric",
    month: "long",
    day: "numeric"
  }).format(new Date(`${value}T00:00:00+09:00`));
