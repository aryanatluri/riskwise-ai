import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const MODE = (import.meta.env.VITE_AUTH_MODE as string) || "dev";
const API = (import.meta.env.VITE_API_URL as string) || "";
const TOKEN_KEY = "riskwise.devToken";

let supabase: SupabaseClient | null = null;
if (MODE === "supabase") {
  supabase = createClient(import.meta.env.VITE_SUPABASE_URL as string, import.meta.env.VITE_SUPABASE_ANON_KEY as string);
}

export const authMode = MODE as "dev" | "supabase";

function readStored(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export async function getToken(): Promise<string | null> {
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    return data.session?.access_token ?? null;
  }
  return readStored();
}

/** Dev: returns once signed in. Supabase: sends a magic link and returns "sent". */
export async function signIn(email: string): Promise<"signed-in" | "sent"> {
  if (supabase) {
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    if (error) throw new Error(error.message);
    return "sent";
  }
  const r = await fetch(`${API}/api/v1/dev/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!r.ok) throw new Error("Dev sign-in is not available on this server");
  const { access_token } = await r.json();
  try {
    sessionStorage.setItem(TOKEN_KEY, access_token);
  } catch {
    /* storage blocked: token lives for this page only */
  }
  return "signed-in";
}

export async function signOut(): Promise<void> {
  if (supabase) await supabase.auth.signOut();
  try {
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("riskwise.org");
  } catch {
    /* ignore */
  }
}

export function onAuthChange(cb: () => void): () => void {
  if (!supabase) return () => {};
  const { data } = supabase.auth.onAuthStateChange(() => cb());
  return () => data.subscription.unsubscribe();
}
