const AUTH_STATE_CHANGE_EVENT = "auth-state-change";

function notifyAuthStateChange() {
  window.dispatchEvent(new Event(AUTH_STATE_CHANGE_EVENT));
}

export function storeAccessToken(token: string) {
  localStorage.setItem("access_token", token);
  notifyAuthStateChange();
}

export function clearAccessToken() {
  localStorage.removeItem("access_token");
  notifyAuthStateChange();
}

export function subscribeToAuthState(onStoreChange: () => void) {
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(AUTH_STATE_CHANGE_EVENT, onStoreChange);

  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(AUTH_STATE_CHANGE_EVENT, onStoreChange);
  };
}

export function getLoggedInSnapshot() {
  return Boolean(localStorage.getItem("access_token"));
}

export function getServerSnapshot() {
  return false;
}
