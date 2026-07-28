import type { MenuType, ReservationStatus } from "~/types/api";

export const mapMenuType = (value: string | null | undefined): MenuType => {
  if (value === "premium" || value === "takeout" || value === "kr") return value;
  if (value === "일품") return "premium";
  if (value === "포장") return "takeout";
  return "kr";
};

export const menuBadgeClass = (value: string | null | undefined) => {
  const type = mapMenuType(value);
  if (type === "premium") return "bg-amber-100 text-amber-800 border-amber-200";
  if (type === "takeout") return "bg-blue-100 text-blue-800 border-blue-200";
  return "bg-green-100 text-green-800 border-green-200";
};

export const reservationStatusClass: Record<ReservationStatus, string> = {
  reserved: "bg-green-100 text-green-800 border-green-200",
  used: "bg-blue-100 text-blue-800 border-blue-200",
  cancelled: "bg-red-100 text-red-800 border-red-200",
  no_show: "bg-amber-100 text-amber-800 border-amber-200"
};
