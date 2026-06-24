import { useEffect, useState } from "react";

type Theme = "dark" | "light";

/** Light/dark theme, persisted to localStorage and applied as `.light` on <html>
 * (the CSS variables in index.css do the rest). Defaults to dark. */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem("mc-theme") as Theme) || "dark",
  );
  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    localStorage.setItem("mc-theme", theme);
  }, [theme]);
  return { theme, toggle: () => setTheme((t) => (t === "dark" ? "light" : "dark")) };
}
