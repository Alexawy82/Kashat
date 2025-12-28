"use client";

import { Moon, Sun, Monitor } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Avoid hydration mismatch
  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <div className={cn("flex items-center gap-1 p-1 rounded-lg bg-muted h-10 w-28", className)}>
        <div className="h-8 w-8 rounded-md bg-muted animate-pulse" />
        <div className="h-8 w-8 rounded-md bg-muted animate-pulse" />
        <div className="h-8 w-8 rounded-md bg-muted animate-pulse" />
      </div>
    );
  }

  return (
    <div className={cn("flex items-center gap-1 p-1 rounded-lg bg-muted", className)}>
      <button
        onClick={() => setTheme("light")}
        className={cn(
          "p-2 rounded-md transition-colors",
          theme === "light"
            ? "bg-background shadow-sm"
            : "hover:bg-background/50"
        )}
        aria-label="Light mode"
        aria-pressed={theme === "light"}
      >
        <Sun className="h-4 w-4" />
      </button>
      <button
        onClick={() => setTheme("dark")}
        className={cn(
          "p-2 rounded-md transition-colors",
          theme === "dark"
            ? "bg-background shadow-sm"
            : "hover:bg-background/50"
        )}
        aria-label="Dark mode"
        aria-pressed={theme === "dark"}
      >
        <Moon className="h-4 w-4" />
      </button>
      <button
        onClick={() => setTheme("system")}
        className={cn(
          "p-2 rounded-md transition-colors",
          theme === "system"
            ? "bg-background shadow-sm"
            : "hover:bg-background/50"
        )}
        aria-label="System theme"
        aria-pressed={theme === "system"}
      >
        <Monitor className="h-4 w-4" />
      </button>
    </div>
  );
}

// Simple dropdown version for compact spaces
export function ThemeToggleDropdown() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return null;
  }

  const themes = [
    { value: "light", label: "Light", icon: Sun },
    { value: "dark", label: "Dark", icon: Moon },
    { value: "system", label: "System", icon: Monitor },
  ];

  const current = themes.find(t => t.value === theme) || themes[2];
  const Icon = current.icon;

  return (
    <button
      onClick={() => {
        const idx = themes.findIndex(t => t.value === theme);
        const next = themes[(idx + 1) % themes.length];
        setTheme(next.value);
      }}
      className="p-2 rounded-md hover:bg-muted transition-colors"
      aria-label={`Current theme: ${current.label}. Click to toggle.`}
    >
      <Icon className="h-5 w-5" />
    </button>
  );
}
