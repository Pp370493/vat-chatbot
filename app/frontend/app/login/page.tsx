"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Scale, ShieldCheck, UserCheck, ShieldAlert, KeyRound, Lock, ArrowRight } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL } from "../config";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [selectedRole, setSelectedRole] = useState<"officer" | "senior_officer" | "admin">("officer");
  const [password, setPassword] = useState("pass1234");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const roleProfiles = {
    officer: {
      name: "นายสมชาย หน้างาน (Officer)",
      email: "officer@rd.go.th",
      roleLabel: "เจ้าหน้าที่หน้างาน (Officer)",
      roleBadge: "สิทธิ์: ถาม-ตอบข้อหารือ VAT",
      badgeColor: "bg-blue-100 text-blue-800 border-blue-200",
      description: "ถาม-ตอบข้อหารือ และดูประวัติข้อหารือเฉพาะของตนเอง 5 ครั้งล่าสุด",
      icon: UserCheck,
      iconColor: "text-blue-600 bg-blue-50 border-blue-200",
    },
    senior_officer: {
      name: "นางสาวสมศรี รุ่นพี่หัวหน้างาน (Supervisor)",
      email: "supervisor@rd.go.th",
      roleLabel: "เจ้าหน้าที่รุ่นพี่ / หัวหน้างาน (Senior)",
      roleBadge: "สิทธิ์: ตรวจสอบและอนุมัติข้อหารือ",
      badgeColor: "bg-amber-100 text-amber-800 border-amber-200",
      description: "เข้าถึงคิวเคสความเสี่ยงสูง (Escalation) ตรวจสอบ แก้ไข และอนุมัติคำตอบ",
      icon: ShieldAlert,
      iconColor: "text-amber-600 bg-amber-50 border-amber-200",
    },
    admin: {
      name: "ดร.สมศักดิ์ ผู้ดูแลระบบ (Admin)",
      email: "admin@rd.go.th",
      roleLabel: "ผู้ดูแลระบบและผู้บริหาร (Admin)",
      roleBadge: "สิทธิ์สูงสุด: ดูแดชบอร์ด & Audit Log",
      badgeColor: "bg-emerald-100 text-emerald-800 border-emerald-200",
      description: "ดูสถิติภาพรวม ธรรมาภิบาล AI และตรวจสอบประวัติ Audit Log ที่แก้ไขไม่ได้",
      icon: ShieldCheck,
      iconColor: "text-emerald-600 bg-emerald-50 border-emerald-200",
    },
  };

  const handleLogin = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsLoading(true);
    setErrorMsg("");

    const target = roleProfiles[selectedRole];
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: target.email,
          password: password,
        }),
      });

      if (!res.ok) {
        throw new Error("เข้าสู่ระบบไม่สำเร็จ กรุณาตรวจสอบรหัสผ่าน");
      }

      const data = await res.json();
      login({
        user_id: data.user_id,
        full_name: data.full_name,
        email: data.email,
        role: data.role,
        session_token: data.session_token,
      });

      // นำทางตามสิทธิ์ที่เหมาะสม
      if (data.role === "officer") {
        router.push("/chat");
      } else if (data.role === "senior_officer") {
        router.push("/review");
      } else {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ Authentication ได้");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 min-h-0 overflow-y-auto bg-slate-900 flex items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-xl bg-slate-800/90 border border-slate-700 rounded-2xl shadow-2xl p-6 sm:p-8 backdrop-blur-md">
        {/* Logo & Header */}
        <div className="text-center mb-6">
          <div className="w-14 h-14 rounded-2xl bg-blue-600 flex items-center justify-center text-white mx-auto mb-3 shadow-lg ring-4 ring-blue-500/20">
            <Scale className="w-8 h-8" />
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center justify-center gap-2">
            Enterprise Tax Co-Pilot
            <span className="text-xs bg-blue-500/20 text-blue-400 font-medium px-2 py-0.5 rounded border border-blue-400/30">
              VAT Registration
            </span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            ระบบยืนยันตัวตนและการควบคุมสิทธิ์ (Role-Based Access Control - RBAC)
          </p>
        </div>

        {/* Quick Role Switcher for Thesis Demo */}
        <div className="mb-6">
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5 flex items-center justify-between">
            <span>เลือกบทบาทสำหรับทดสอบสาธิต (Demo Role):</span>
            <span className="text-[11px] text-blue-400 font-normal">คลิกเลือกเพื่อสลับบทบาท</span>
          </label>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {(["officer", "senior_officer", "admin"] as const).map((r) => {
              const info = roleProfiles[r];
              const Icon = info.icon;
              const isSelected = selectedRole === r;

              return (
                <button
                  type="button"
                  key={r}
                  onClick={() => setSelectedRole(r)}
                  className={`p-3 rounded-xl border text-left transition flex flex-col justify-between ${
                    isSelected
                      ? "bg-blue-600/20 border-blue-500 ring-2 ring-blue-500/50 shadow-md"
                      : "bg-slate-800 border-slate-700 hover:bg-slate-700/60 text-slate-400"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`p-1.5 rounded-lg border ${info.iconColor}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className={`text-xs font-bold ${isSelected ? "text-white" : "text-slate-300"}`}>
                      {r === "officer" ? "เจ้าหน้าที่" : r === "senior_officer" ? "หัวหน้างาน" : "Admin"}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400 line-clamp-2 leading-snug">
                    {info.description}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected Role Card Info */}
        <div className="bg-slate-900/80 rounded-xl p-4 border border-slate-700 mb-6 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">ชื่อผู้ใช้งาน:</span>
            <span className="text-xs font-semibold text-white">
              {roleProfiles[selectedRole].name}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">อีเมลทางการ:</span>
            <span className="text-xs font-mono text-slate-300">
              {roleProfiles[selectedRole].email}
            </span>
          </div>
          <div className="flex items-center justify-between pt-1 border-t border-slate-800">
            <span className="text-xs text-slate-400">ระดับสิทธิ์ (RBAC):</span>
            <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${roleProfiles[selectedRole].badgeColor}`}>
              {roleProfiles[selectedRole].roleBadge}
            </span>
          </div>
        </div>

        {/* Password Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-blue-400" />
              <span>รหัสผ่านเข้าใช้งาน (Demo Default: pass1234)</span>
            </label>
            <div className="relative">
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="กรอกรหัสผ่าน..."
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
              />
              <Lock className="w-4 h-4 text-slate-500 absolute right-3.5 top-3" />
            </div>
          </div>

          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-500/20 border border-rose-500/40 text-rose-300 text-xs">
              {errorMsg}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 text-white rounded-xl font-bold text-sm transition shadow-lg flex items-center justify-center gap-2 group"
          >
            <span>{isLoading ? "กำลังยืนยันสิทธิ์และบันทึก Audit Log..." : "เข้าสู่ระบบและเริ่มใช้งาน"}</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition" />
          </button>
        </form>

        <div className="mt-5 text-center text-[11px] text-slate-500">
          🔒 บันทึกประวัติการเข้าใช้งานลง Immutable Audit Log ตามมาตรฐาน ISO/IEC 27001
        </div>
      </div>
    </div>
  );
}
