import { AxiosError } from 'axios';

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const message = error.response?.data?.error ?? error.message;
    const details = error.response?.data?.details;
    return details ? `${message}: ${details}` : message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Unexpected error occurred';
}
