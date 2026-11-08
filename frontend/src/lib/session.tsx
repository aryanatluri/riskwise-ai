import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, setOrg } from "./api";
import { getToken, onAuthChange } from "./auth";
import type { Org } from "./types";

interface Session {
  ready: boolean;
  signedIn: boolean;
  email: string;
  orgs: Org[];
  org: Org | null;
  selectOrg: (id: string) => void;
  refresh: () => Promise<void>;
}

const Ctx = createContext<Session | null>(null);
const ORG_KEY = "riskwise.org";

function storedOrg(): string | null {
  try {
    return localStorage.getItem(ORG_KEY);
  } catch {
    return null;
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [email, setEmail] = useState("");
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [org, setOrgState] = useState<Org | null>(null);

  const refresh = useCallback(async () => {
    const token = await getToken();
    if (!token) {
      setSignedIn(false);
      setReady(true);
      return;
    }
    try {
      const me = await api.get<{ email: string }>("/api/v1/me");
      const list = await api.get<Org[]>("/api/v1/orgs");
      setEmail(me.email);
      setOrgs(list);
      const pick = list.find((o) => o.id === storedOrg()) ?? list[0] ?? null;
      setOrg(pick?.id ?? null);
      setOrgState(pick);
      setSignedIn(true);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setSignedIn(false);
      else throw e;
    } finally {
      setReady(true);
    }
  }, []);

  useEffect(() => {
    refresh();
    return onAuthChange(() => refresh());
  }, [refresh]);

  const selectOrg = (id: string) => {
    const o = orgs.find((x) => x.id === id) ?? null;
    setOrg(o?.id ?? null);
    setOrgState(o);
    try {
      if (o) localStorage.setItem(ORG_KEY, o.id);
    } catch {
      /* ignore */
    }
  };

  return (
    <Ctx.Provider value={{ ready, signedIn, email, orgs, org, selectOrg, refresh }}>{children}</Ctx.Provider>
  );
}

export function useSession(): Session {
  const s = useContext(Ctx);
  if (!s) throw new Error("useSession outside provider");
  return s;
}

export function canReview(org: Org | null) {
  return org?.role === "admin" || org?.role === "reviewer";
}
export function isAdmin(org: Org | null) {
  return org?.role === "admin";
}
