import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTime(isoString: string): string {
  try {
    return new Date(isoString).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  } catch {
    return '--:--:--';
  }
}

export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export function getStatusColor(status: number | undefined): string {
  if (!status) return 'text-gray-500';
  if (status < 300) return 'text-green-500';
  if (status < 400) return 'text-blue-500';
  if (status < 500) return 'text-yellow-500';
  return 'text-red-500';
}

export function getStatusBgColor(status: number | undefined): string {
  if (!status) return 'bg-gray-100';
  if (status < 300) return 'bg-green-100';
  if (status < 400) return 'bg-blue-100';
  if (status < 500) return 'bg-yellow-100';
  return 'bg-red-100';
}

export function getMethodColor(method: string): string {
  const colors: Record<string, string> = {
    GET: 'bg-green-100 text-green-700',
    POST: 'bg-blue-100 text-blue-700',
    PUT: 'bg-yellow-100 text-yellow-700',
    PATCH: 'bg-orange-100 text-orange-700',
    DELETE: 'bg-red-100 text-red-700',
    OPTIONS: 'bg-gray-100 text-gray-700',
    HEAD: 'bg-gray-100 text-gray-700',
  };
  return colors[method] || 'bg-gray-100 text-gray-700';
}

export function truncatePath(path: string, maxLength: number = 50): string {
  if (path.length <= maxLength) return path;
  return path.slice(0, maxLength - 3) + '...';
}
