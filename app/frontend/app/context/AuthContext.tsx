"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { apiFetch, SESSION_KEY } from "../lib/api";

export type Role = "officer" | "senior_officer" | "admin";

export interface UserProfile {
  user_id: string;
  full_name: string;
  email: string;
  role: Role;
  session_token: string;
}

interface AuthContextType {
  user: UserProfile | null;
  login: (profile: UserProfile) => void;
  logout: () => Promise<void>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: () => {},
  logout: async () => {},
  isLoading: true,
});

// หน้าที่แต่ละบทบาทเข้าได้ (backend ตรวจสิทธิ์ซ้ำทุกคำขอ — ฝั่งเว็บแค่พาไปหน้าที่ถูก)
const PAGE_ROLES: Record<string, Role[]> = {
  "/review": ["senior_officer", "admin"],
  "/dashboard": ["admin"],
  "/test": ["admin"],
};

export function homeFor(role: Role): string {
  return role === "senior_officer" ? "/review" : role === "admin" ? "/dashboard" : "/chat";
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // โหลด session จาก localStorage แล้วยืนยันกับ backend ว่ายังใช้ได้และบทบาทถูกต้อง
    const saved = localStorage.getItem(SESSION_KEY);
    if (!saved) {
      setIsLoading(false);
      return;
    }
    let parsed: UserProfile | null = null;
    try {
      parsed = JSON.parse(saved);
    } catch {
      localStorage.removeItem(SESSION_KEY);
    }
    if (!parsed) {
      setIsLoading(false);
      return;
    }
    apiFetch("/api/v1/auth/me")
      .then(async (res) => {
        if (res.ok) {
          const me = await res.json();
          const verified = { ...parsed!, role: me.role, full_name: me.full_name, email: me.email };
          setUser(verified);
          localStorage.setItem(SESSION_KEY, JSON.stringify(verified));
        } else {
          localStorage.removeItem(SESSION_KEY);
        }
      })
      .catch(() => setUser(parsed)) // backend ไม่ตอบ: ใช้ข้อมูลเดิมไปก่อน คำขอถัดไปจะถูกตรวจอีกครั้ง
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      if (pathname !== "/login") router.replace("/login");
      return;
    }
    const allowed = PAGE_ROLES[pathname];
    if (allowed && !allowed.includes(user.role)) router.replace(homeFor(user.role));
  }, [isLoading, user, pathname, router]);

  const login = (profile: UserProfile) => {
    setUser(profile);
    localStorage.setItem(SESSION_KEY, JSON.stringify(profile));
  };

  const logout = async () => {
    try {
      await apiFetch("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // ออกจากระบบฝั่งเว็บต่อแม้ backend ไม่ตอบ
    }
    setUser(null);
    localStorage.removeItem(SESSION_KEY);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
