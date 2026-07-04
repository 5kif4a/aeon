/** Memento Mori life-in-weeks math. */

export const LIFE_EXPECTANCY_YEARS = 90;
export const WEEKS_PER_YEAR = 52;
export const TOTAL_LIFE_WEEKS = LIFE_EXPECTANCY_YEARS * WEEKS_PER_YEAR;
const MS_PER_WEEK = 7 * 24 * 60 * 60 * 1000;

export interface LifeStats {
  age: number;
  isFutureDate: boolean;
  ninetiethBirthday: Date;
  percent: number;
  weeksLeft: number;
  weeksLived: number;
}

export function parseLocalDate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function calculateAge(birthDate: Date, now: Date): number {
  let age = now.getFullYear() - birthDate.getFullYear();
  const hasBirthdayPassed =
    now.getMonth() > birthDate.getMonth() ||
    (now.getMonth() === birthDate.getMonth() && now.getDate() >= birthDate.getDate());
  if (!hasBirthdayPassed) age -= 1;
  return Math.max(age, 0);
}

export function calculateLifeStats(birthDateValue: string): LifeStats {
  const birthDate = parseLocalDate(birthDateValue);
  const now = new Date();
  const isFutureDate = birthDate > now;
  const rawWeeksLived = isFutureDate
    ? 0
    : Math.floor((now.getTime() - birthDate.getTime()) / MS_PER_WEEK);
  const weeksLived = Math.min(Math.max(rawWeeksLived, 0), TOTAL_LIFE_WEEKS);
  const weeksLeft = Math.max(TOTAL_LIFE_WEEKS - weeksLived, 0);
  const percent = Math.min(100, Math.round((weeksLived / TOTAL_LIFE_WEEKS) * 100));
  const age = isFutureDate ? 0 : calculateAge(birthDate, now);
  const ninetiethBirthday = new Date(birthDate);
  ninetiethBirthday.setFullYear(ninetiethBirthday.getFullYear() + LIFE_EXPECTANCY_YEARS);

  return { age, isFutureDate, ninetiethBirthday, percent, weeksLeft, weeksLived };
}

export function formatDateOnly(value: Date, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(value);
}

export function formatDiaryDate(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function todayKey(): string {
  const date = new Date();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}
