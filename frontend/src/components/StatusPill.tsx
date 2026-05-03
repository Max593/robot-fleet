import { Wifi, WifiOff } from "lucide-react";

export function StatusPill({ online }: { online: boolean }) {
  return (
    <span className={`pill ${online ? "pill-online" : "pill-offline"}`}>
      {online ? <Wifi size={14} aria-hidden="true" /> : <WifiOff size={14} aria-hidden="true" />}
      {online ? "online" : "offline"}
    </span>
  );
}
