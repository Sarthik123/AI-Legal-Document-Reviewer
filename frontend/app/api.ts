export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production"
    ? "https://api.lawyerlens.in"
    : "http://127.0.0.1:8000");
