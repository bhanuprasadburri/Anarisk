import { useState, useEffect } from 'react';

export interface Toast {
  id: string;
  title: string;
  description?: string;
  type?: 'default' | 'success' | 'warning' | 'error';
  duration?: number;
}

let listeners: Array<(toasts: Toast[]) => void> = [];
let memoryToasts: Toast[] = [];

export const toast = (options: {
  title: string;
  description?: string;
  type?: 'default' | 'success' | 'warning' | 'error';
  duration?: number;
}) => {
  const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
  const newToast: Toast = {
    id,
    title: options.title,
    description: options.description,
    type: options.type || 'default',
    duration: options.duration || 4000,
  };

  memoryToasts = [...memoryToasts, newToast];
  listeners.forEach((l) => l(memoryToasts));

  setTimeout(() => {
    memoryToasts = memoryToasts.filter((t) => t.id !== id);
    listeners.forEach((l) => l(memoryToasts));
  }, newToast.duration);
};

export const useToast = () => {
  const [toasts, setToasts] = useState<Toast[]>(memoryToasts);

  useEffect(() => {
    listeners.push(setToasts);
    return () => {
      listeners = listeners.filter((l) => l !== setToasts);
    };
  }, []);

  const dismiss = (id: string) => {
    memoryToasts = memoryToasts.filter((t) => t.id !== id);
    listeners.forEach((l) => l(memoryToasts));
  };

  return { toasts, toast, dismiss };
};
