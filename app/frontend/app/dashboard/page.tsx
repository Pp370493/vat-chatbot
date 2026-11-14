"use client";

import React, { useState, useEffect } from "react";
import {
  BarChart3,
  TrendingUp,
  ShieldCheck,
  AlertTriangle,
  FileText,
  RefreshCw,
  HelpCircle,
  Database,
  Award,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";
import Link from "next/link";
import { Lock, ArrowLeft, Shield } from "lucide-react";
import { API_BASE_URL } from "../config";

interface OverviewStats {
  total_queries: number;
  in_scope_ratio: number;
  escalation_rate: number;
  auto_answer_rate: number;
  top_repeated_questions: { text: string; count: number }[];
}

interface HeatmapItem {
  topic: string;
  escalation_count: number;
}

interface AuditLogEntry {
  id: string;
  query_id: string | null;
  event_type: string;
  event_data: any;
  actor_type: string;
  actor_name: string;
  actor_role: string;
  created_at: string;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<OverviewStats | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // ตรวจสอบสิทธิ์ RBAC (ตัวเลือก A: เฉพาะ admin เท่านั้น)
  const isAuthorized = user?.role === "admin";

  const fetchDashboardData = async () => {
    setIsLoading(true);
    try {
      const [resOverview, resHeatmap, resLogs] = await Promise.all([
        fetch(`${API_BASE_URL}/api/v1/analytics/overview`),
        fetch(`${API_BASE_URL}/api/v1/analytics/heatmap`),
        fetch(`${API_BASE_URL}/api/v1/analytics/audit-logs?limit=15`),
      ]);

      if (resOverview.ok) {
        setStats(await resOverview.json());
      }
      if (resHeatmap.ok) {
        setHeatmap(await resHeatmap.json());
      }
      if (resLogs.ok) {
        setAuditLogs(await resLogs.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthorized) {
      fetchDashboardData();
    }
  }, [user]);

  if (!isAuthorized) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center p-6 bg-slate-100">
        <div className="bg-white rounded-2xl max-w-md w-full p-8 shadow-xl border border-slate-200 text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-rose-100 text-rose-600 flex items-center justify-center mx-auto shadow-inner">
            <Lock className="w-8 h-8" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              คุณไม่มีสิทธิ์เข้าถึงหน้านี้ (403 Forbidden)
            </h2>
            <p className="text-xs text-slate-500 mt-2 leading-relaxed">
              หน้านี้สงวนไว้สำหรับ <span className="font-semibold text-emerald-700">ผู้ดูแลระบบและผู้บริหาร (Admin)</span> เท่านั้น <br />
              บทบาทปัจจุบันของคุณคือ: <span className="font-mono font-bold text-blue-600">{user?.full_name || "เจ้าหน้าที่ (Officer)"}</span>
            </p>
          </div>
          <div className="pt-2">
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs shadow transition"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>กลับไปหน้าถาม-ตอบข้อหารือ</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 max-w-7xl mx-auto w-full space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-blue-600" />
            แดชบอร์ดสถิติและการกำกับดูแล (Admin Intelligence & Governance)
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            ข้อมูลเชิงลึกสรุปจากระบบ Enterprise Tax Co-Pilot สำหรับผู้บริหารและอาจารย์ที่ปรึกษา (NIDA MADT IS)
          </p>
        </div>

        <button
          onClick={fetchDashboardData}
          disabled={isLoading}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 transition shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          <span>รีเฟรชสถิติ</span>
        </button>
      </div>

      {/* KPI Stat Cards (4 Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Queries */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold mb-2">
            <span>คำถามทั้งหมด (Total Queries)</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <FileText className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-slate-900">{stats?.total_queries || 0}</div>
          <div className="text-[11px] text-slate-400 mt-2 flex items-center gap-1">
            <span className="text-blue-600 font-medium">บันทึกใน SQLite จริง</span>
          </div>
        </div>

        {/* Card 2: In-Scope Ratio */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold mb-2">
            <span>ความตรงตามสโคป (In-Scope Ratio)</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-emerald-600">
            {stats ? (stats.in_scope_ratio * 100).toFixed(1) : 0}%
          </div>
          <div className="text-[11px] text-slate-400 mt-2">ผ่านการคัดกรองโดย Agent 1</div>
        </div>

        {/* Card 3: Auto-Answer Rate */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold mb-2">
            <span>ตอบอัตโนมัติ (Auto-Answer Rate)</span>
            <div className="w-8 h-8 rounded-lg bg-teal-50 text-teal-600 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-teal-600">
            {stats ? (stats.auto_answer_rate * 100).toFixed(1) : 0}%
          </div>
          <div className="text-[11px] text-slate-400 mt-2">Trust Score ≥ 60%</div>
        </div>

        {/* Card 4: Escalation Rate */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold mb-2">
            <span>เข้าคิวหัวหน้างาน (Escalation Rate)</span>
            <div className="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-rose-600">
            {stats ? (stats.escalation_rate * 100).toFixed(1) : 0}%
          </div>
          <div className="text-[11px] text-slate-400 mt-2">Human-in-the-loop Approved</div>
        </div>
      </div>

      {/* Grid: Heatmap + Top Questions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Heatmap & Risk Distribution */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <h2 className="text-sm font-bold text-slate-900 mb-1 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-blue-600" />
            การกระจายตัวของระดับความเสี่ยง (Risk Tier Breakdown)
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            สัดส่วนการตัดสินใจของ Agent 6 ตามเกณฑ์ประกาศอธิบดีฯ ฉบับที่ 57 ข้อ 6
          </p>

          <div className="space-y-3">
            {heatmap.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-xs">ยังไม่มีข้อมูลสถิติ</div>
            ) : (
              heatmap.map((item, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-semibold text-slate-700">
                      {item.topic === "auto_answer"
                        ? "ตอบอัตโนมัติ (Auto Answer)"
                        : item.topic === "senior_review"
                        ? "ความเสี่ยงสูง (Senior Review)"
                        : "ตรวจโดยรุ่นพี่ (Officer Review)"}
                    </span>
                    <span className="font-bold text-slate-900">{item.escalation_count} เคส</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                    <div
                      className={`h-2.5 rounded-full ${
                        item.topic === "auto_answer"
                          ? "bg-emerald-500"
                          : item.topic === "senior_review"
                          ? "bg-rose-500"
                          : "bg-amber-500"
                      }`}
                      style={{
                        width: `${Math.min(
                          100,
                          (item.escalation_count / (stats?.total_queries || 1)) * 100
                        )}%`,
                      }}
                    ></div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Top Repeated Questions */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <h2 className="text-sm font-bold text-slate-900 mb-1 flex items-center gap-2">
            <HelpCircle className="w-4 h-4 text-blue-600" />
            คำถามยอดนิยมที่พบบ่อย (Top Inquiries)
          </h2>
          <p className="text-xs text-slate-500 mb-4">
            นำไปใช้ในการจัดทำคู่มือและ FAQ กลางสำหรับฝึกอบรมเจ้าหน้าที่ (Feature C2 & C3)
          </p>

          <div className="divide-y divide-slate-100">
            {!stats?.top_repeated_questions || stats.top_repeated_questions.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-xs">ยังไม่มีประวัติคำถามซ้ำ</div>
            ) : (
              stats.top_repeated_questions.map((q, idx) => (
                <div key={idx} className="py-2.5 flex items-start justify-between gap-3 text-xs">
                  <div className="flex items-start gap-2">
                    <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-600 font-bold flex items-center justify-center text-[10px] flex-shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <span className="text-slate-800 line-clamp-2">{q.text}</span>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-bold text-[11px] flex-shrink-0">
                    {q.count} ครั้ง
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Knowledge Base Governance (Final Scope A5) */}
      <div className="bg-slate-900 text-white p-6 rounded-xl shadow-md border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold flex items-center gap-2 text-slate-100">
              <Database className="w-4 h-4 text-blue-400" />
              การกำกับดูแลคลังความรู้ (Knowledge Governance - Final Scope A5)
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              คำตอบต้องมาจากเอกสารประกาศทางการที่ได้รับอนุมัติแล้วเท่านั้น (Single Source of Truth)
            </p>
          </div>
          <span className="px-2.5 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-medium">
            Status: Approved
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="bg-slate-800/80 p-3.5 rounded-lg border border-slate-700">
            <div className="text-slate-400 mb-1">เอกสารกฎหมายทางการ</div>
            <div className="font-semibold text-slate-200">
              ประกาศอธิบดีกรมสรรพากร (ฉบับที่ 57)
            </div>
            <div className="text-[11px] text-emerald-400 mt-1">10 Chunks Indexed</div>
          </div>

          <div className="bg-slate-800/80 p-3.5 rounded-lg border border-slate-700">
            <div className="text-slate-400 mb-1">ความคงที่ของคำตอบ (Consistency)</div>
            <div className="font-semibold text-slate-200">Deterministic Guaranteed</div>
            <div className="text-[11px] text-blue-400 mt-1">Resolved Query Temperature = 0.0</div>
          </div>

          <div className="bg-slate-800/80 p-3.5 rounded-lg border border-slate-700">
            <div className="text-slate-400 mb-1">การเติบโตของคลังความรู้ (KB Growth)</div>
            <div className="font-semibold text-slate-200">Admin Approval Workflow</div>
            <div className="text-[11px] text-amber-400 mt-1">
              ห้ามใช้ประสบการณ์จนกว่าจะได้รับอนุมัติ
            </div>
          </div>
        </div>
      </div>

      {/* Immutable Audit Log Viewer (ISO/IEC 27001 Compliance) */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div>
            <h3 className="text-sm font-bold flex items-center gap-2 text-slate-800">
              <Shield className="w-4 h-4 text-emerald-600" />
              บันทึกการตรวจสอบย้อนหลังที่แก้ไขไม่ได้ (Immutable Audit Log - ISO/IEC 27001)
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              บันทึกทุก Action ในระบบ ไม่สามารถแก้ไขหรือลบได้ (Append-Only Trigger Lock) และตัดข้อมูล PII ออก
            </p>
          </div>
          <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-xs font-semibold flex items-center gap-1">
            <Lock className="w-3 h-3" />
            Append-Only Enforced
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="bg-slate-50 text-slate-500 border-b border-slate-200">
                <th className="py-2.5 px-3 font-semibold">เวลา (Timestamp)</th>
                <th className="py-2.5 px-3 font-semibold">ประเภทเหตุการณ์ (Event)</th>
                <th className="py-2.5 px-3 font-semibold">ผู้ดำเนินการ (Actor)</th>
                <th className="py-2.5 px-3 font-semibold">บทบาท (Role)</th>
                <th className="py-2.5 px-3 font-semibold">รายละเอียด (Metadata)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-slate-400">
                    ยังไม่มีบันทึก Audit Log ในระบบ
                  </td>
                </tr>
              ) : (
                auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/60 transition font-mono">
                    <td className="py-2.5 px-3 text-slate-600 whitespace-nowrap text-[11px]">
                      {log.created_at ? new Date(log.created_at).toLocaleString("th-TH") : "-"}
                    </td>
                    <td className="py-2.5 px-3 font-sans">
                      <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                        {log.event_type}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-sans text-slate-700 font-medium">
                      {log.actor_name}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="uppercase text-[10px] font-bold text-blue-600">
                        {log.actor_role}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-[10.5px] text-slate-500 max-w-xs truncate font-mono">
                      {typeof log.event_data === "object" ? JSON.stringify(log.event_data) : String(log.event_data)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
