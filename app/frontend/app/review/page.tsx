"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Edit3,
  Clock,
  AlertTriangle,
  RefreshCw,
  Search,
  BookOpen,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";
import Link from "next/link";
import { Lock, ArrowLeft } from "lucide-react";
import { API_BASE_URL } from "../config";

interface EscalationItem {
  escalation_id: string;
  query_id: string;
  tier: string;
  decision: string | null;
  final_answer: string | null;
  raw_text: string;
  resolved_query: string;
  draft_text: string;
  citations: { text_span: string; source_section: string }[];
  confidence_score: number;
  risk_factors: string[];
  trust_score: number;
  created_at: string;
}

export default function ReviewPage() {
  const { user } = useAuth();
  const [escalations, setEscalations] = useState<EscalationItem[]>([]);
  const [selectedCase, setSelectedCase] = useState<EscalationItem | null>(null);
  const [statusFilter, setStatusFilter] = useState<"pending" | "reviewed">("pending");
  const [editedAnswer, setEditedAnswer] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // ตรวจสอบสิทธิ์ RBAC (ตัวเลือก A: ถ้าไม่ใช่ senior_officer หรือ admin จะไม่ให้เข้า)
  const isAuthorized = user?.role === "senior_officer" || user?.role === "admin";

  const fetchEscalations = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/escalations?status=${statusFilter}`);
      if (res.ok) {
        const data = await res.json();
        setEscalations(data);
        if (data.length > 0) {
          setSelectedCase(data[0]);
          setEditedAnswer(data[0].final_answer || data[0].draft_text);
        } else {
          setSelectedCase(null);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEscalations();
  }, [statusFilter]);

  const handleDecision = async (decision: "approved" | "edited" | "rejected") => {
    if (!selectedCase) return;
    setIsSubmitting(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/v1/escalations/${selectedCase.escalation_id}/decision`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            decision: decision,
            final_answer: editedAnswer,
            reviewed_by: "หัวหน้างาน (Supervisor-01)",
          }),
        }
      );

      if (res.ok) {
        alert(`บันทึกผลการตรวจสอบ (${decision}) เรียบร้อยแล้วค่ะ`);
        fetchEscalations();
      } else {
        alert("เกิดข้อผิดพลาดในการบันทึก");
      }
    } catch (e) {
      console.error(e);
      alert("ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์");
    } finally {
      setIsSubmitting(false);
    }
  };

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
              หน้านี้สงวนไว้สำหรับ <span className="font-semibold text-amber-700">เจ้าหน้าที่รุ่นพี่ (Supervisor)</span> หรือ <span className="font-semibold text-emerald-700">ผู้ดูแลระบบ (Admin)</span> เท่านั้น <br />
              บัญชีปัจจุบันของคุณคือ: <span className="font-mono font-bold text-blue-600">{user?.full_name || "เจ้าหน้าที่หน้างาน (Officer)"}</span>
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
    <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 max-w-7xl mx-auto w-full">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-amber-500" />
            คิวพิจารณาอนุมัติของหัวหน้างาน (Supervisor Approval View)
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            เคสที่ระบบ AI ตรวจพบความเสี่ยงสูงหรือข้อหารือซับซ้อนตามประกาศอธิบดีฯ ฉบับที่ 57 ข้อ 6 (Human-in-the-loop)
          </p>
        </div>

        {/* Tab Filters */}
        <div className="flex items-center gap-2">
          <div className="bg-slate-200/80 p-1 rounded-lg flex text-xs font-medium">
            <button
              onClick={() => setStatusFilter("pending")}
              className={`px-3 py-1.5 rounded-md transition ${
                statusFilter === "pending"
                  ? "bg-white text-slate-900 shadow-sm font-semibold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              รอการตรวจสอบ
            </button>
            <button
              onClick={() => setStatusFilter("reviewed")}
              className={`px-3 py-1.5 rounded-md transition ${
                statusFilter === "reviewed"
                  ? "bg-white text-slate-900 shadow-sm font-semibold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              ตรวจสอบแล้ว
            </button>
          </div>

          <button
            onClick={fetchEscalations}
            disabled={isLoading}
            className="p-2 border border-slate-300 rounded-lg hover:bg-slate-100 text-slate-600 transition"
            title="รีเฟรชข้อมูล"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Main Split Content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: List of Escalations (5 Cols) */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden flex flex-col h-[calc(100vh-14rem)]">
          <div className="p-3 bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600 flex items-center justify-between">
            <span>รายการคำขอ ({escalations.length} เคส)</span>
            <span className="text-[11px] text-slate-400">เรียงตามเวลาล่าสุด</span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {escalations.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                ไม่มีรายการเคสค้างในคิวนี้
              </div>
            ) : (
              escalations.map((item) => (
                <div
                  key={item.escalation_id}
                  onClick={() => {
                    setSelectedCase(item);
                    setEditedAnswer(item.final_answer || item.draft_text);
                  }}
                  className={`p-4 cursor-pointer transition text-left ${
                    selectedCase?.escalation_id === item.escalation_id
                      ? "bg-blue-50/70 border-l-4 border-blue-600"
                      : "hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase ${
                        item.tier === "senior_review"
                          ? "bg-rose-100 text-rose-800"
                          : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {item.tier === "senior_review" ? "ระดับสูง (Senior)" : "เจ้าหน้าที่รุ่นพี่"}
                    </span>
                    <span className="text-[11px] text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(item.created_at).toLocaleTimeString("th-TH", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>

                  <div className="text-xs font-medium text-slate-800 line-clamp-2 mb-2">
                    {item.raw_text}
                  </div>

                  {item.risk_factors && item.risk_factors.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {item.risk_factors.map((rf, i) => (
                        <span
                          key={i}
                          className="text-[10px] bg-rose-50 text-rose-700 px-1.5 py-0.5 rounded border border-rose-200"
                        >
                          {rf}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Case Review & Decision Detail (7 Cols) */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl shadow-sm p-6 flex flex-col space-y-5">
          {selectedCase ? (
            <>
              {/* Case Query Box */}
              <div>
                <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                  คำถามข้อหารือจากเจ้าหน้าที่หน้างาน
                </div>
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 font-medium">
                  {selectedCase.raw_text}
                </div>
              </div>

              {/* Detected Risk Analysis */}
              <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-lg text-xs space-y-2">
                <div className="font-bold text-rose-900 flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-rose-600" />
                  การวิเคราะห์ความเสี่ยงจากระบบ (Agent 6 Risk Assessment)
                </div>
                <div className="text-rose-800">
                  <span className="font-semibold">ปัจจัยความเสี่ยงที่ตรวจพบ:</span>{" "}
                  {selectedCase.risk_factors.join(", ") || "ประเด็นข้อกฎหมายซับซ้อน"}
                </div>
                <div className="flex gap-4 text-rose-700 text-[11px]">
                  <span>Trust Score: {((selectedCase.trust_score || 0) * 100).toFixed(0)}%</span>
                  <span>
                    Confidence: {((selectedCase.confidence_score || 0) * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* AI Drafted Answer */}
              <div>
                <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center justify-between">
                  <span>ร่างคำตอบของ AI (Grounded Draft)</span>
                  <span className="text-[11px] text-blue-600 font-medium flex items-center gap-1">
                    <BookOpen className="w-3 h-3" />
                    อ้างอิง: {selectedCase.citations.map((c) => c.source_section).join(", ")}
                  </span>
                </div>
                <div className="p-3.5 bg-blue-50/50 border border-blue-200 rounded-lg text-xs text-slate-700 leading-relaxed max-h-36 overflow-y-auto">
                  {selectedCase.draft_text}
                </div>
              </div>

              {/* Editable Final Answer */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5 flex items-center gap-1">
                  <Edit3 className="w-3.5 h-3.5 text-blue-600" />
                  คำวินิจฉัย/คำตอบสุดท้ายของหัวหน้างาน (Final Answer):
                </label>
                <textarea
                  rows={4}
                  value={editedAnswer}
                  onChange={(e) => setEditedAnswer(e.target.value)}
                  className="w-full text-xs p-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 font-sans leading-relaxed"
                  placeholder="พิมพ์แก้ไขหรือปรับปรุงคำตอบก่อนยืนยัน..."
                />
              </div>

              {/* Action Buttons */}
              <div className="pt-2 border-t border-slate-200 flex flex-wrap items-center justify-end gap-3">
                <button
                  onClick={() => handleDecision("rejected")}
                  disabled={isSubmitting}
                  className="px-4 py-2 border border-rose-300 text-rose-700 hover:bg-rose-50 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  <XCircle className="w-4 h-4" />
                  <span>ปฏิเสธ (Reject)</span>
                </button>

                <button
                  onClick={() => handleDecision("edited")}
                  disabled={isSubmitting}
                  className="px-4 py-2 border border-blue-600 text-blue-600 hover:bg-blue-50 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
                >
                  <Edit3 className="w-4 h-4" />
                  <span>แก้ไขและอนุมัติ (Edit & Approve)</span>
                </button>

                <button
                  onClick={() => handleDecision("approved")}
                  disabled={isSubmitting}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-sm transition"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>อนุมัติตามร่าง (Approve Draft)</span>
                </button>
              </div>
            </>
          ) : (
            <div className="py-20 text-center text-slate-400 text-sm">
              กรุณาเลือกเคสจากรายการทางซ้ายเพื่อพิจารณา
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
