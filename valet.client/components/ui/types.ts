// components/ui/types.ts
import { ButtonHTMLAttributes, InputHTMLAttributes } from 'react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant: 'ghost' | 'solid' | 'outline';
  size: 'sm' | 'md' | 'lg' | 'icon';
}

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string;
}