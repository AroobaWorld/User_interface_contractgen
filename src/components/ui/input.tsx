import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn("focus:outline-none focus:ring-2 focus:ring-[#4A90E2]", className)}
      {...props}
    />
  );
}
