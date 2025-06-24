import { createFileRoute } from "@tanstack/react-router";
import { useEffect } from "react";

function LogoutPage() {

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_URL}/logout`, { method: "POST", credentials: "include" })
      .finally(() => {
        localStorage.clear();
        sessionStorage.clear();
        if (window.indexedDB && indexedDB.databases) {
          indexedDB.databases().then(dbs => {
            dbs.forEach(db => db.name && indexedDB.deleteDatabase(db.name));
          });
        }

      });
  }, []);

  return <div>Logging out...</div>;
}

export const Route = createFileRoute("/logout")({
  beforeLoad: () => {
    // Always redirect to login after component runs
    return undefined;
  },
  component: LogoutPage,
});