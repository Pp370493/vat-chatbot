"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquare, ShieldCheck, BarChart3, Scale, LogOut, ChevronDown, UserCheck, ShieldAlert, FlaskConical } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export function Navbar() {
  const { user, logout, switchRole } = useAuth();
  const pathname = usePathname();
  const [isSwitchMenuOpen, setIsSwitchMenuOpen] = useState(false);

  // ถ้าอยู่หน้า Login ไม่ต้องแสดงแถบนำทาง
  if (pathname === "/login") {
    return null;
  }

  const role = user?.role || "officer";

  const roleNames = {
    officer: "เจ้าหน้าที่หน้างาน (Officer)",
    senior_officer: "รุ่นพี่หัวหน้างาน (Supervisor)",
    admin: "ผู้บริหารและแอดมิน (Admin)",
  };

  const roleBadges = {
    officer: "bg-blue-500/20 text-blue-400 border-blue-400/30",
    senior_officer: "bg-amber-500/20 text-amber-400 border-amber-400/30",
    admin: "bg-emerald-500/20 text-emerald-400 border-emerald-400/30",
  };

  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 flex-shrink-0 z-50 shadow-md">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo & Title */}
        <div className="flex items-center space-x-3">
          <Link href="/chat" className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-inner hover:bg-blue-500 transition">
            <Scale className="w-6 h-6" />
          </Link>
          <div>
            <h1 className="font-bold text-sm sm:text-base leading-tight text-slate-100 flex items-center gap-2">
              Enterprise Tax Co-Pilot
              <span className="text-[10px] sm:text-xs bg-blue-500/20 text-blue-400 font-medium px-2 py-0.5 rounded border border-blue-400/30">
                VAT Registration
              </span>
            </h1>
            <p className="text-[11px] sm:text-xs text-slate-400 hidden sm:block">
              ระบบผู้ช่วยอัจฉริยะสำหรับเจ้าหน้าที่กรมสรรพากร (NIDA MADT IS)
            </p>
          </div>
        </div>

        {/* Navigation Tabs - Filtered by RBAC (ตัวเลือก A: ซ่อนเมนูที่ไม่มีสิทธิ์) */}
        <nav className="flex items-center space-x-1 sm:space-x-2">
          {/* ถาม-ตอบข้อหารือ: เข้าได้ทุก Role */}
          <Link
            href="/chat"
            className={`flex items-center gap-1.5 sm:gap-2 px-3 py-1.5 sm:px-3.5 sm:py-2 rounded-lg text-xs sm:text-sm font-medium transition ${
              pathname === "/chat"
                ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
            }`}
          >
            <MessageSquare className="w-4 h-4 text-blue-400" />
            <span>ถาม-ตอบข้อหารือ</span>
          </Link>

          {/* คิวตรวจหัวหน้างาน: เฉพาะ senior_officer และ admin */}
          {(role === "senior_officer" || role === "admin") && (
            <Link
              href="/review"
              className={`flex items-center gap-1.5 sm:gap-2 px-3 py-1.5 sm:px-3.5 sm:py-2 rounded-lg text-xs sm:text-sm font-medium transition ${
                pathname === "/review"
                  ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                  : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
              }`}
            >
              <ShieldCheck className="w-4 h-4 text-amber-400" />
              <span>คิวตรวจหัวหน้างาน</span>
            </Link>
          )}

          {/* แดชบอร์ดสถิติ & Governance: เฉพาะ admin */}
          {role === "admin" && (
            <Link
              href="/dashboard"
              className={`flex items-center gap-1.5 sm:gap-2 px-3 py-1.5 sm:px-3.5 sm:py-2 rounded-lg text-xs sm:text-sm font-medium transition ${
                pathname === "/dashboard"
                  ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                  : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
              }`}
            >
              <BarChart3 className="w-4 h-4 text-emerald-400" />
              <span>แดชบอร์ดสถิติ</span>
            </Link>
          )}
          {/* ชุดทดสอบ Benchmark: เข้าได้ทุก Role */}
          <Link
            href="/test"
            className={`flex items-center gap-1.5 sm:gap-2 px-3 py-1.5 sm:px-3.5 sm:py-2 rounded-lg text-xs sm:text-sm font-medium transition ${
              pathname === "/test"
                ? "bg-slate-800 text-white border border-slate-700 shadow-sm"
                : "text-slate-300 hover:bg-slate-800/60 hover:text-white"
            }`}
          >
            <FlaskConical className="w-4 h-4 text-purple-400" />
            <span>ชุดทดสอบ Benchmark</span>
          </Link>
        </nav>

        {/* User Role Badge & Fast Switcher */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {user ? (
            <div className="relative">
              <button
                onClick={() => setIsSwitchMenuOpen(!isSwitchMenuOpen)}
                className="flex items-center gap-2 p-1.5 sm:px-2.5 sm:py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-800 border border-slate-700 transition text-left"
                title="คลิกเพื่อสลับ Role (Demo Fast Switcher)"
              >
                <div className="text-right hidden md:block">
                  <div className="text-xs font-semibold text-slate-200">{user.full_name}</div>
                  <div className={`text-[10px] font-medium px-1.5 py-0.2 rounded border inline-block ${roleBadges[role]}`}>
                    {roleNames[role]}
                  </div>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              </button>

              {/* Dropdown Role Switcher */}
              {isSwitchMenuOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl py-1 z-50 text-xs">
                  <div className="px-3 py-1.5 text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-700 font-semibold">
                    สลับบทบาททดสอบ (Quick Switch):
                  </div>
                  <button
                    onClick={() => {
                      switchRole("officer");
                      setIsSwitchMenuOpen(false);
                    }}
                    className={`w-full px-3 py-2 text-left flex items-center justify-between hover:bg-slate-700 transition ${
                      role === "officer" ? "text-blue-400 font-bold bg-slate-700/40" : "text-slate-200"
                    }`}
                  >
                    <span>เจ้าหน้าที่หน้างาน (Officer)</span>
                    {role === "officer" && <span>✓</span>}
                  </button>
                  <button
                    onClick={() => {
                      switchRole("senior_officer");
                      setIsSwitchMenuOpen(false);
                    }}
                    className={`w-full px-3 py-2 text-left flex items-center justify-between hover:bg-slate-700 transition ${
                      role === "senior_officer" ? "text-amber-400 font-bold bg-slate-700/40" : "text-slate-200"
                    }`}
                  >
                    <span>หัวหน้างาน (Supervisor)</span>
                    {role === "senior_officer" && <span>✓</span>}
                  </button>
                  <button
                    onClick={() => {
                      switchRole("admin");
                      setIsSwitchMenuOpen(false);
                    }}
                    className={`w-full px-3 py-2 text-left flex items-center justify-between hover:bg-slate-700 transition ${
                      role === "admin" ? "text-emerald-400 font-bold bg-slate-700/40" : "text-slate-200"
                    }`}
                  >
                    <span>ผู้ดูแลระบบ (Admin)</span>
                    {role === "admin" && <span>✓</span>}
                  </button>

                  <div className="border-t border-slate-700 mt-1 pt-1">
                    <button
                      onClick={() => {
                        logout();
                        setIsSwitchMenuOpen(false);
                      }}
                      className="w-full px-3 py-2 text-left text-rose-400 hover:bg-rose-500/10 flex items-center gap-2 transition"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      <span>ออกจากระบบ (Logout)</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <Link
              href="/login"
              className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition shadow"
            >
              เข้าสู่ระบบ
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
