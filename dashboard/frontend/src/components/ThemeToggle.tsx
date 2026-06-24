import { Moon, Sun } from "lucide-react";

export function ThemeToggle({ theme, onToggle }: { theme: string; onToggle: () => void }) {
  const dark = theme === "dark";
  return (
    <button
      onClick={onToggle}
      title={dark ? "Switch to light" : "Switch to dark"}
      aria-label="Toggle theme"
      className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-line bg-panel2/50 text-muted transition hover:border-accent/60 hover:text-accent"
    >
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}
