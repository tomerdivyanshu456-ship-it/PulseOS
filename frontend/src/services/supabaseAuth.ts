const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL?.replace(/\/$/, "");
const SUPABASE_PUBLISHABLE_KEY = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
const VERIFIER_KEY = "pulseos_supabase_pkce_verifier";
const SESSION_KEY = "pulseos_supabase_session";

export function isSupabaseAuthConfigured(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_PUBLISHABLE_KEY);
}

function requireSupabaseConfig(): { url: string; key: string } {
  if (!SUPABASE_URL || !SUPABASE_PUBLISHABLE_KEY) {
    throw new Error("Google sign-in is not configured. Set the Supabase URL and publishable key.");
  }
  return { url: SUPABASE_URL, key: SUPABASE_PUBLISHABLE_KEY };
}

function toBase64Url(bytes: Uint8Array): string {
  let binary = "";
  bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export async function startGoogleSignIn(): Promise<void> {
  const { url } = requireSupabaseConfig();
  const verifierBytes = crypto.getRandomValues(new Uint8Array(64));
  const verifier = toBase64Url(verifierBytes);
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  const challenge = toBase64Url(new Uint8Array(digest));
  sessionStorage.setItem(VERIFIER_KEY, verifier);

  const redirectTo = window.location.origin + window.location.pathname;
  const authorizeUrl = new URL(`${url}/auth/v1/authorize`);
  authorizeUrl.searchParams.set("provider", "google");
  authorizeUrl.searchParams.set("redirect_to", redirectTo);
  authorizeUrl.searchParams.set("code_challenge", challenge);
  authorizeUrl.searchParams.set("code_challenge_method", "s256");
  window.location.assign(authorizeUrl.toString());
}

export async function completeGoogleSignIn(): Promise<boolean> {
  const currentUrl = new URL(window.location.href);
  const code = currentUrl.searchParams.get("code");
  if (!code) return false;

  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  if (!verifier) throw new Error("Google sign-in session expired. Please try again.");
  const { url, key } = requireSupabaseConfig();
  const response = await fetch(`${url}/auth/v1/token?grant_type=pkce`, {
    method: "POST",
    headers: { "Content-Type": "application/json", apikey: key },
    body: JSON.stringify({ auth_code: code, code_verifier: verifier }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.msg || payload.message || "Google sign-in could not be completed.");
  }

  sessionStorage.setItem(SESSION_KEY, JSON.stringify(payload));
  sessionStorage.removeItem(VERIFIER_KEY);
  currentUrl.searchParams.delete("code");
  currentUrl.searchParams.delete("state");
  window.history.replaceState({}, document.title, currentUrl.pathname + currentUrl.search + currentUrl.hash);
  return true;
}

export function getGoogleUserEmail(): string | null {
  try {
    const session = JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null");
    return typeof session?.user?.email === "string" ? session.user.email : null;
  } catch {
    return null;
  }
}


export function getSupabaseAccessToken(): string | null {
  try {
    const session = JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null");
    return typeof session?.access_token === "string" ? session.access_token : null;
  } catch {
    return null;
  }
}
