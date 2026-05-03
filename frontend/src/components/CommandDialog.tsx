import { useEffect, useState } from "react";
import { Send, X } from "lucide-react";
import { commandLabels, pauseDurationOptions } from "../constants";
import type { CommandType, Robot } from "../types";

type CommandDialogProps = {
  robot: Robot | null;
  isSending: boolean;
  error: string | null;
  onClose: () => void;
  onSend: (commandType: CommandType, payload: Record<string, unknown>) => void;
};

export function CommandDialog({ robot, isSending, error, onClose, onSend }: CommandDialogProps) {
  const [selectedCommand, setSelectedCommand] = useState<CommandType>("run_diagnostic");
  const [pauseDuration, setPauseDuration] = useState(30);

  useEffect(() => {
    if (robot !== null) {
      setSelectedCommand("run_diagnostic");
      setPauseDuration(30);
    }
  }, [robot?.robot_id]);

  if (robot === null) {
    return null;
  }

  const sendCommand = () => {
    const payload: Record<string, unknown> =
      selectedCommand === "pause_for"
        ? {
            duration_seconds: pauseDuration
          }
        : {};
    onSend(selectedCommand, payload);
  };

  return (
    <div className="modalBackdrop" role="presentation">
      <section className="commandDialog" role="dialog" aria-modal="true" aria-labelledby="commandDialogTitle">
        <div className="dialogHeader">
          <div>
            <p className="eyebrow">Robot Command</p>
            <h2 id="commandDialogTitle">{robot.robot_id}</h2>
          </div>
          <button className="iconButton" type="button" onClick={onClose} aria-label="Close command dialog">
            <X size={18} aria-hidden="true" />
          </button>
        </div>

        <label className="fieldControl">
          <span>Command</span>
          <select
            value={selectedCommand}
            onChange={(event) => setSelectedCommand(event.target.value as CommandType)}
          >
            {(Object.keys(commandLabels) as CommandType[]).map((commandType) => (
              <option key={commandType} value={commandType}>
                {commandLabels[commandType]}
              </option>
            ))}
          </select>
        </label>

        {selectedCommand === "pause_for" ? (
          <label className="fieldControl">
            <span>Duration</span>
            <select value={pauseDuration} onChange={(event) => setPauseDuration(Number(event.target.value))}>
              {pauseDurationOptions.map((duration) => (
                <option key={duration} value={duration}>
                  {duration}s
                </option>
              ))}
            </select>
          </label>
        ) : null}

        {error ? <div className="notice error dialogNotice">{error}</div> : null}

        <div className="dialogActions">
          <button className="secondaryButton" type="button" onClick={onClose}>
            Cancel
          </button>
          <button className="primaryButton" type="button" onClick={sendCommand} disabled={isSending}>
            <Send size={16} aria-hidden="true" />
            {isSending ? "Sending" : "Send"}
          </button>
        </div>
      </section>
    </div>
  );
}
