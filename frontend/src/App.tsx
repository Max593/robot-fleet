import { useCallback, useEffect, useState } from "react";
import { queueRobotCommand } from "./api/robots";
import { CommandDialog } from "./components/CommandDialog";
import { ToastStack } from "./components/ToastStack";
import { commandLabels } from "./constants";
import { DashboardPage } from "./pages/DashboardPage";
import { RobotDetailPage } from "./pages/RobotDetailPage";
import type { CommandType, Robot, Theme, Toast } from "./types";
import { getRouteRobotId } from "./utils/routing";
import { getInitialTheme } from "./utils/theme";

function App() {
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [selectedRobot, setSelectedRobot] = useState<Robot | null>(null);
  const [isSendingCommand, setIsSendingCommand] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [commandError, setCommandError] = useState<string | null>(null);
  const [theme, setTheme] = useState<Theme>(getInitialTheme);
  const [routeRobotId, setRouteRobotId] = useState<string | null>(getRouteRobotId);
  const [commandRefreshSignal, setCommandRefreshSignal] = useState(0);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("robot-fleet-theme", theme);
  }, [theme]);

  useEffect(() => {
    const handlePopState = () => setRouteRobotId(getRouteRobotId());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigateToRobot = (robotId: string) => {
    window.history.pushState(null, "", `/robots/${encodeURIComponent(robotId)}`);
    setRouteRobotId(robotId);
  };

  const navigateToDashboard = () => {
    window.history.pushState(null, "", "/");
    setRouteRobotId(null);
  };

  const dismissToast = useCallback((toastId: number) => {
    setToasts((currentToasts) => currentToasts.filter((toast) => toast.id !== toastId));
  }, []);

  const addToast = useCallback(
    (message: string) => {
      const toastId = Date.now() + Math.random();
      setToasts((currentToasts) => [...currentToasts, { id: toastId, message }]);
      window.setTimeout(() => dismissToast(toastId), 10000);
    },
    [dismissToast]
  );

  const openCommandDialog = (robot: Robot) => {
    setSelectedRobot(robot);
    setCommandError(null);
  };

  const closeCommandDialog = () => {
    setSelectedRobot(null);
    setCommandError(null);
  };

  const sendCommand = async (commandType: CommandType, payload: Record<string, unknown>) => {
    if (selectedRobot === null) {
      return;
    }

    try {
      setIsSendingCommand(true);
      setCommandError(null);
      await queueRobotCommand(selectedRobot.robot_id, commandType, payload);
      addToast(`${commandLabels[commandType]} queued for ${selectedRobot.robot_id}`);
      setCommandRefreshSignal((currentSignal) => currentSignal + 1);
      setSelectedRobot(null);
    } catch (err) {
      setCommandError(err instanceof Error ? err.message : "Unable to queue command");
    } finally {
      setIsSendingCommand(false);
    }
  };

  const updateLastRefreshTime = useCallback((updatedAt: Date) => {
    setLastUpdatedAt(updatedAt);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((currentTheme) => (currentTheme === "dark" ? "light" : "dark"));
  }, []);

  return (
    <main className="shell">
      {routeRobotId ? (
        <RobotDetailPage
          robotId={routeRobotId}
          lastUpdatedAt={lastUpdatedAt}
          theme={theme}
          commandRefreshSignal={commandRefreshSignal}
          onBack={navigateToDashboard}
          onOpenCommand={openCommandDialog}
          onRefreshTime={updateLastRefreshTime}
          onToggleTheme={toggleTheme}
        />
      ) : (
        <DashboardPage
          lastUpdatedAt={lastUpdatedAt}
          theme={theme}
          onNavigateToRobot={navigateToRobot}
          onOpenCommand={openCommandDialog}
          onRefreshTime={updateLastRefreshTime}
          onToggleTheme={toggleTheme}
        />
      )}

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
      <CommandDialog
        robot={selectedRobot}
        isSending={isSendingCommand}
        error={commandError}
        onClose={closeCommandDialog}
        onSend={(commandType, payload) => void sendCommand(commandType, payload)}
      />
    </main>
  );
}

export default App;
