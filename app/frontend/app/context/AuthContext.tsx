"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { API_BASE_URL } from "../config";

export interface UserProfile {
  user_id: string;
  full_name: string;
  email: string;
  role: "officer" | "senior_officer" | "admin";
  session_token: string;
}

interface AuthContextType {
  user: UserProfile | null;
  login: (profile: UserProfile) => void;
  logout: () => void;
  switchRole: (role: "officer" | "senior_officer" | "admin") => Promise<void>;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: () => {},
  logout: () => {},
  switchRole: async () => {},
  isLoading: true,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // โหลด session จาก localStorage เมื่อเริ่มต้น
    const saved = localStorage.getItem("tax_copilot_user");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setUser(parsed);
      } catch (e) {
        console.error("Failed to parse saved user", e);
      }
    }
    setIsLoading(false);
  }, []);

  const login = (profile: UserProfile) => {
    setUser(profile);
    localStorage.setItem("tax_copilot_user", JSON.stringify(profile));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("tax_copilot_user");
    router.push("/login");
  };

  const switchRole = async (targetRole: "officer" | "senior_officer" | "admin") => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/quick-switch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: targetRole }),
      });
      if (res.ok) {
        const data = await res.json();
        const updated: UserProfile = {
          user_id: data.user_id,
          full_name: data.full_name,
          email: data.email,
          role: data.role,
          session_token: data.session_token,
        };
        login(updated);
      }
    } catch (e) {
      console.error("Quick switch failed", e);
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, switchRole, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
