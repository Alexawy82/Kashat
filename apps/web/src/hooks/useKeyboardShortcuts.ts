import { useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";

interface KeyboardShortcutsOptions {
  enabled?: boolean;
  onSearch?: () => void;
}

export function useKeyboardShortcuts(options: KeyboardShortcutsOptions = {}) {
  const { enabled = true, onSearch } = options;
  const router = useRouter();

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Don't trigger shortcuts in input fields
      const target = event.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.contentEditable === "true"
      ) {
        return;
      }

      // Cmd/Ctrl + K for search
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        onSearch?.();
        return;
      }

      // G-based navigation (vim-style)
      if (event.key === "g" && !event.metaKey && !event.ctrlKey) {
        const handleSecondKey = (e: KeyboardEvent) => {
          switch (e.key) {
            case "d":
              e.preventDefault();
              router.push("/");
              break;
            case "t":
              e.preventDefault();
              router.push("/transactions");
              break;
            case "b":
              e.preventDefault();
              router.push("/bills");
              break;
            case "r":
              e.preventDefault();
              router.push("/subscriptions");
              break;
            case "u":
              e.preventDefault();
              router.push("/budget");
              break;
            case "i":
              e.preventDefault();
              router.push("/import");
              break;
            case "s":
              e.preventDefault();
              router.push("/settings");
              break;
          }
          window.removeEventListener("keydown", handleSecondKey);
        };

        // Listen for the second key for 1 second
        window.addEventListener("keydown", handleSecondKey);
        setTimeout(() => {
          window.removeEventListener("keydown", handleSecondKey);
        }, 1000);
        return;
      }

      // ? for help/shortcuts modal
      if (event.key === "?") {
        // Could open a shortcuts help modal
        console.log("Keyboard shortcuts help:");
        console.log("g+d: Dashboard");
        console.log("g+t: Transactions");
        console.log("g+a: Analytics");
        console.log("g+b: Budget");
        console.log("g+c: Calendar");
        console.log("g+r: Recurring");
        console.log("g+i: Import");
        console.log("g+s: Settings");
        console.log("Cmd/Ctrl+K: Search");
        return;
      }
    },
    [router, onSearch]
  );

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [enabled, handleKeyDown]);
}
