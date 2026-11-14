/**
 * Centralized API Base URL configuration for VAT Co-Pilot Frontend.
 * - When deployed on Vercel: uses relative path "" to route through Next.js API Routes / proxy.
 * - When running in custom dev with external API: can be overridden via NEXT_PUBLIC_API_BASE_URL.
 */
export const API_BASE_URL =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE_URL
    ? process.env.NEXT_PUBLIC_API_BASE_URL.replace(/\/$/, "")
    : "";
