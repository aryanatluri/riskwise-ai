import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { signOut } from "../lib/auth";
import { isAdmin, useSession } from "../lib/session";
import type { Finding } from "../lib/types";

export function Layout() {
  const { org, orgs, selectOrg, email, refresh } = useSession();
  const nav = useNavigate();
  const [openCount, setOpenCount] = useState<number | null>(null);

  useEffect(() => {
    if (!org) return;
    api
      .get<Finding[]>("/api/v1/findings?status=open&limit=1000")
      .then((f) => setOpenCount(f.length))
      .catch(() => setOpenCount(null));
  }, [org]);

  return (
    <div className="shell">
      <aside className="side">
        <a className="brand" href="/">
          <span className="brand-mark" aria-hidden="true" />
          RISKWISE
        </a>
        {orgs.length > 1 && (
          <div className="org-switch">
            <label className="small muted" htmlFor="org-select">
              Organization
            </label>
            <select id="org-select" value={org?.id} onChange={(e) => selectOrg(e.target.value)}>
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          </div>
        )}
        <nav className="nav" aria-label="Main">
          <NavLink to="/review">
            Review queue {openCount ? <span className="count">{openCount}</span> : null}
          </NavLink>
          <NavLink to="/contracts">Contracts</NavLink>
          <NavLink to="/policies">Policies</NavLink>
          {isAdmin(org) && <NavLink to="/settings">Settings</NavLink>}
          {isAdmin(org) && <NavLink to="/audit">Audit log</NavLink>}
        </nav>
        <div className="side-foot">
          <span>{org?.name}</span>
          <span>{email}</span>
          <button
            className="btn-quiet"
            style={{ padding: 0, justifyContent: "flex-start" }}
            onClick={async () => {
              await signOut();
              await refresh();
              nav("/");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet key={org?.id} />
      </main>
    </div>
  );
}
