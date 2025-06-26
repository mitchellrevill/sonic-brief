import { createFileRoute } from "@tanstack/react-router";
import { useEffect } from "react";
import { logoutUser } from "@/lib/api";

function LogoutPage() {
  useEffect(() => {
    logoutUser()
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