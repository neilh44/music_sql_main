// In src/components/ui/Button.tsx
import React from "react";

interface ButtonProps {
  children: React.ReactNode;
  variant: "ghost" | "outline" | "solid";
  size: "sm" | "icon" | "lg";
  className?: string;
  onClick?: () => void | Promise<void>;
  disabled?: boolean; // Add this line
}

export const Button: React.FC<ButtonProps> = ({ 
  children, 
  variant, 
  size, 
  className, 
  onClick, 
  disabled = false // Add a default value
}) => {
  // Define button styles based on variant and size
  const variantClasses = {
    ghost: "bg-transparent text-green-500 border border-green-500",
    outline: "border-2 border-green-500 text-green-500",
    solid: "bg-green-500 text-white"
  };

  const sizeClasses = {
    sm: "text-sm py-2 px-4",
    icon: "p-2", // For icons
    lg: "text-lg py-3 px-6"
  };

  return (
    <button
      className={`${variantClasses[variant]} ${sizeClasses[size]} rounded ${className}`}
      onClick={onClick}
      disabled={disabled} // Add disabled attribute
    >
      {children}
    </button>
  );
};