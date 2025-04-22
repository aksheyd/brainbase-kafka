// Utility for merging and deduplicating Tailwind CSS class names
// Combines clsx (conditional className logic) with tailwind-merge for best results
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Returns a single string of merged class names
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
