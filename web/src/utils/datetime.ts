const pad = (value: number): string => value.toString().padStart(2, '0');

const toDate = (value: string | null | undefined): Date | null => {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
};

export function toLocalInputValue(isoString: string | null | undefined): string {
  const date = toDate(isoString);
  if (!date) {
    return '';
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}

export function toLocalDateInput(isoString: string | null | undefined): string {
  const date = toDate(isoString);
  if (!date) {
    return '';
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function toLocalTimeInput(isoString: string | null | undefined): string {
  const date = toDate(isoString);
  if (!date) {
    return '';
  }
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

const getTodayIsoDate = (): string => {
  const today = new Date();
  return `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;
};

export function isFutureDate(dateValue: string | null | undefined): boolean {
  if (!dateValue) {
    return false;
  }
  return dateValue > getTodayIsoDate();
}

export function toIsoString(localValue: string | null | undefined): string {
  const date = toDate(localValue);
  return (date ?? new Date()).toISOString();
}

export function combineDateAndTime(date: string, time: string | null | undefined): string {
  if (!date) {
    return new Date().toISOString();
  }
  const safeTime = time && time.trim() ? time : '00:00';
  const composed = `${date}T${safeTime}`;
  const parsed = new Date(composed);
  return Number.isNaN(parsed.getTime()) ? new Date().toISOString() : parsed.toISOString();
}

export function getCurrentTimeInput(): string {
  const now = new Date();
  return `${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

export function formatDateTime(value: string): string {
  const date = toDate(value);
  if (!date) {
    return value;
  }
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours()
  )}:${pad(date.getMinutes())}`;
}
