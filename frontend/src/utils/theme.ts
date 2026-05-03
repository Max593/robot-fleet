import type { Theme } from "../types";

export function getInitialTheme(): Theme {
  const storedTheme = window.localStorage.getItem("robot-fleet-theme");
  return storedTheme === "dark" ? "dark" : "light";
}
