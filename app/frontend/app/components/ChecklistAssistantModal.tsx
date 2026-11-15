"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Building,
  User,
  MapPin,
  ShieldAlert,
  Send,
  RefreshCw,
  Sparkles,
  CheckSquare,
  Square,
} from "lucide-react";
import { apiFetch } from "../lib/api";

interface ChecklistItem {
  id: string;
  category: string;
  title: string;
  details: string;
  legal_ref: string;
  is_mandatory: boolean;
  status?: "received" | "missing" | "not_applicable";
}

interface ChecklistAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPostSummaryToChat: (summaryText: string) => void;
  staffUserId?: string;
  conversationId?: string;
}

export default function ChecklistAssistantModal({
  isOpen,
  onClose,
  onPostSummaryToChat,
  staffUserId,
  conversationId,
}: ChecklistAssistantModalProps) {
  // 1. Profile State (คุณลักษณะผู้ยื่นคำขอ)
  const [channel, setChannel] = useState<string>("paper");
  const [taxpayerType, setTaxpayerType] = useState<string>("individual_thai");
  const [locationType, setLocationType] = useState<string>("rented");
  const [isPowerOfAttorney, setIsPowerOfAttorney] = useState<boolean>(false);

  // 2. Checklist & Evaluation State
  const [checklistItems, setChecklistItems] = useState<ChecklistItem[]>([]);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [evaluationResult, setEvaluationResult] = useState<any>(null);

  // Auto-generate checklist when profile changes or modal opens
  const fetchChecklist = async () => {
    setIsGenerating(true);
    setEvaluationResult(null);
    try {
      const res = await apiFetch(`/api/v1/chat/form-session/generate-checklist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          channel,
          taxpayer_type: taxpayerType,
          location_type: locationType,
          is_power_of_attorney: isPowerOfAttorney,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        // default all items to "missing" so officer explicitly checks received items
        const initialItems = (data.items || []).map((it: ChecklistItem) => ({
          ...it,
          status: "missing",
        }));
        setChecklistItems(initialItems);
      }
    } catch (e) {
      console.error("Error generating checklist:", e);
    } finally {
      setIsGenerating(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchChecklist();
    }
  }, [isOpen, channel, taxpayerType, locationType, isPowerOfAttorney]);

  if (!isOpen) return null;

  // Toggle item status
  const handleToggleStatus = (id: string) => {
    setChecklistItems((prev) =>
      prev.map((item) => {
        if (item.id === id) {
          const nextStatus = item.status === "received" ? "missing" : "received";
          return { ...item, status: nextStatus };
        }
        return item;
      })
    );
    setEvaluationResult(null); // reset evaluation until clicked again
  };

  // Select / Deselect All
  const handleSelectAll = (select: boolean) => {
    setChecklistItems((prev) =>
      prev.map((item) => ({
        ...item,
        status: select ? "received" : "missing",
      }))
    );
    setEvaluationResult(null);
  };

  // Evaluate Checklist
  const handleEvaluate = async () => {
    setIsEvaluating(true);
    try {
      const profile = {
        channel,
        taxpayer_type: taxpayerType,
        location_type: locationType,
        is_power_of_attorney: isPowerOfAttorney,
      };
      const res = await apiFetch(`/api/v1/chat/form-session/evaluate-checklist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile,
          items: checklistItems,
          staff_user_id: staffUserId,
        }),
      });
      if (res.ok) {
        const result = await res.json();
        setEvaluationResult(result);
      }
    } catch (e) {
      console.error("Error evaluating checklist:", e);
    } finally {
      setIsEvaluating(false);
    }
  };

  // Send summary to chat
  const handleSendToChat = () => {
    if (!evaluationResult) return;
    const channelName = channel === "paper" ? "ยื่นแบบกระดาษ (ฉบับ 57)" : "ยื่นผ่านอินเทอร์เน็ต (ฉบับ 159)";
    const summaryMarkdown = (
      `📋 **รายงานผลการตรวจรับเอกสาร ภ.พ.01 (Agent 7 - ข้อ 5)**\n\n` +
      `• **ช่องทางยื่น**: ${channelName}\n` +
      `• **ผลการประเมิน**: **${evaluationResult.verdict_title}**\n` +
      `• **สถานะการตรวจรับ**: ตรวจรับแล้ว ${evaluationResult.received_count} / ${evaluationResult.total_count} รายการ\n\n` +
      `${evaluationResult.verdict_message}`
    );
    onPostSummaryToChat(summaryMarkdown);
    onClose();
  };

  const receivedCount = checklistItems.filter((it) => it.status === "received").length;
  const totalCount = checklistItems.length;
  const progressPercent = totalCount > 0 ? Math.round((receivedCount / totalCount) * 100) : 0;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-5 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* MODAL HEADER */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-blue-700 via-indigo-700 to-blue-800 text-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center text-white border border-white/20 shadow-inner">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-base tracking-tight">ระบบตรวจ Checklist เอกสาร ภ.พ.01 (Agent 7)</h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-400 text-amber-950">
                  เทียบเกณฑ์ข้อ 5
                </span>
              </div>
              <p className="text-xs text-blue-100">
                วิเคราะห์คุณลักษณะผู้ยื่นคำขอ สร้าง Checklist และประเมินความครบถ้วนก่อนรับคำขอจดทะเบียน VAT
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* MODAL BODY */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50">
          {/* STEP 1: ตรวจสอบคุณลักษณะของผู้ยื่นขอจดทะเบียน (Taxpayer Profile) */}
          <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
                  1
                </span>
                <h4 className="font-bold text-slate-800 text-sm">
                  ตรวจสอบคุณลักษณะของผู้ยื่นคำขอจดทะเบียน
                </h4>
              </div>
              <span className="text-[11px] text-slate-500">
                (ระบบจะปรับรายการเอกสารตามข้อ 5 ให้อัตโนมัติ)
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {/* 1.1 ช่องทางการยื่น */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  <Building className="w-3.5 h-3.5 text-blue-600" />
                  <span>1. ช่องทางการยื่น</span>
                </label>
                <select
                  value={channel}
                  onChange={(e) => setChannel(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:bg-white transition text-slate-800 font-medium"
                >
                  <option value="paper">📄 แบบกระดาษ (ฉบับที่ 57) ณ สรรพากรพื้นที่</option>
                  <option value="internet">🌐 ระบบอินเทอร์เน็ต rd.go.th (ฉบับที่ 159)</option>
                </select>
              </div>

              {/* 1.2 ประเภทผู้ประกอบการ */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-blue-600" />
                  <span>2. ประเภทผู้ประกอบการ</span>
                </label>
                <select
                  value={taxpayerType}
                  onChange={(e) => setTaxpayerType(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:bg-white transition text-slate-800 font-medium"
                >
                  <option value="individual_thai">บุคคลธรรมดาสัญชาติไทย</option>
                  <option value="individual_foreigner">บุคคลธรรมดาต่างด้าว (ต่างชาติ)</option>
                  <option value="joint_non_juristic">สามีภริยา / คณะบุคคล / ห้างหุ้นส่วนสามัญ</option>
                  <option value="juristic_thai">นิติบุคคลไทย (บริษัทจำกัด / หจก.)</option>
                  <option value="joint_venture">กิจการร่วมค้า (Joint Venture)</option>
                  <option value="foreign_entity">นิติบุคคลต่างประเทศ (ตั้งตัวแทนในไทย)</option>
                </select>
              </div>

              {/* 1.3 สถานที่ตั้งสถานประกอบการ */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-blue-600" />
                  <span>3. สถานที่ตั้งสถานประกอบการ</span>
                </label>
                <select
                  value={locationType}
                  onChange={(e) => setLocationType(e.target.value)}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:bg-white transition text-slate-800 font-medium"
                >
                  <option value="owned">เป็นกรรมสิทธิ์ของตนเอง (บ้านตนเอง)</option>
                  <option value="rented">เช่าอาคาร / เช่าสถานที่</option>
                  <option value="consent_free">ขอใช้สถานที่ผู้อื่น (ฟรีไม่มีค่าเช่า)</option>
                  <option value="condo_online">คอนโด/ห้องชุด (ขายออนไลน์ มีทะเบียนพาณิชย์)</option>
                  <option value="condo_general">คอนโด/ห้องชุด (ธุรกิจทั่วไป)</option>
                </select>
              </div>

              {/* 1.4 การมอบอำนาจ */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5 text-blue-600" />
                  <span>4. การมอบอำนาจ</span>
                </label>
                <select
                  value={isPowerOfAttorney ? "yes" : "no"}
                  onChange={(e) => setIsPowerOfAttorney(e.target.value === "yes")}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:bg-white transition text-slate-800 font-medium"
                >
                  <option value="no">ผู้ประกอบการมายื่นด้วยตนเอง</option>
                  <option value="yes">มอบอำนาจให้ผู้อื่นมายื่นแทน</option>
                </select>
              </div>
            </div>
          </div>

          {/* STEP 2: รายการ Checklist เอกสารตามข้อ 5 (Interactive Items) */}
          <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-blue-600 text-white text-xs font-bold flex items-center justify-center">
                  2
                </span>
                <div>
                  <h4 className="font-bold text-slate-800 text-sm">
                    รายการเอกสารที่ต้องแนบตามข้อ 5 ของประกาศอธิบดีฯ ({totalCount} รายการ)
                  </h4>
                  <p className="text-xs text-slate-500">
                    ให้เจ้าหน้าที่คลิกติ๊กถูก [✓] ในหัวข้อที่มีเอกสารแนบมาครบถ้วนแล้ว
                  </p>
                </div>
              </div>

              {/* Progress & Quick Buttons */}
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <span className="text-xs font-bold text-slate-700">
                    ตรวจรับแล้ว {receivedCount}/{totalCount} ({progressPercent}%)
                  </span>
                  <div className="w-28 bg-slate-200 h-2 rounded-full overflow-hidden mt-0.5">
                    <div
                      className={`h-full transition-all duration-300 ${
                        progressPercent === 100 ? "bg-emerald-500" : "bg-blue-600"
                      }`}
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                </div>

                <div className="flex items-center gap-1.5 pl-2 border-l border-slate-200">
                  <button
                    onClick={() => handleSelectAll(true)}
                    className="text-[11px] font-semibold text-blue-600 hover:text-blue-700 px-2 py-1 rounded bg-blue-50 hover:bg-blue-100 transition"
                  >
                    ติ๊กครบทั้งหมด
                  </button>
                  <button
                    onClick={() => handleSelectAll(false)}
                    className="text-[11px] font-semibold text-slate-600 hover:text-slate-700 px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 transition"
                  >
                    ล้างทั้งหมด
                  </button>
                </div>
              </div>
            </div>

            {/* Checklist Items List */}
            {isGenerating ? (
              <div className="py-12 flex flex-col items-center justify-center text-slate-400 gap-2">
                <RefreshCw className="w-6 h-6 animate-spin text-blue-600" />
                <span className="text-xs">กำลังเทียบเคียงหลักเกณฑ์ข้อ 5 และสร้าง Checklist...</span>
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                {checklistItems.map((item, index) => {
                  const isChecked = item.status === "received";
                  return (
                    <div
                      key={item.id}
                      onClick={() => handleToggleStatus(item.id)}
                      className={`flex items-start gap-3 p-3.5 rounded-xl border transition cursor-pointer select-none ${
                        isChecked
                          ? "bg-emerald-50/70 border-emerald-300 shadow-xs"
                          : "bg-white hover:bg-slate-50 border-slate-200"
                      }`}
                    >
                      <button
                        type="button"
                        className="mt-0.5 text-slate-400 hover:text-slate-600 focus:outline-none flex-shrink-0"
                      >
                        {isChecked ? (
                          <CheckSquare className="w-5 h-5 text-emerald-600" />
                        ) : (
                          <Square className="w-5 h-5 text-slate-400" />
                        )}
                      </button>

                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1">
                          <span
                            className={`text-xs font-bold ${
                              isChecked ? "text-emerald-900" : "text-slate-800"
                            }`}
                          >
                            {index + 1}. {item.title}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                            {item.legal_ref}
                          </span>
                          {isChecked && (
                            <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-600 text-white">
                              ได้รับแล้ว ✓
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed">{item.details}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* ACTION: ตกลง / สรุปผลความครบถ้วน */}
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
              <span className="text-xs text-slate-500">
                เมื่อตรวจสอบรายการข้างต้นแล้ว กดปุ่ม <b>"ตกลง (ประเมินความครบถ้วน)"</b> เพื่อให้ AI สรุปผล
              </span>
              <button
                onClick={handleEvaluate}
                disabled={isEvaluating || isGenerating || totalCount === 0}
                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl text-xs font-bold transition shadow-md shadow-blue-500/20 disabled:opacity-50"
              >
                {isEvaluating ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                <span>ตกลง (ประเมินความครบถ้วนโดย AI)</span>
              </button>
            </div>
          </div>

          {/* STEP 3: ผลการประเมินความครบถ้วนโดย AI (Evaluation Verdict Card) */}
          {evaluationResult && (
            <div
              className={`rounded-xl p-5 border shadow-sm space-y-4 animate-in slide-in-from-bottom-2 duration-300 ${
                evaluationResult.is_complete
                  ? "bg-emerald-50 border-emerald-300 text-emerald-950"
                  : "bg-amber-50 border-amber-300 text-amber-950"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                      evaluationResult.is_complete
                        ? "bg-emerald-600 text-white"
                        : "bg-amber-500 text-white"
                    }`}
                  >
                    {evaluationResult.is_complete ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : (
                      <AlertTriangle className="w-5 h-5" />
                    )}
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">{evaluationResult.verdict_title}</h4>
                    <p className="text-xs opacity-80">
                      ตรวจรับเอกสารแล้ว {evaluationResult.received_count} รายการ / ขาดอีก{" "}
                      {evaluationResult.missing_count} รายการ
                    </p>
                  </div>
                </div>

                <button
                  onClick={handleSendToChat}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-bold bg-white shadow-sm border border-slate-200 hover:bg-slate-50 transition text-slate-800"
                >
                  <Send className="w-3.5 h-3.5 text-blue-600" />
                  <span>ส่งผลสรุปนี้เข้าห้องแชท</span>
                </button>
              </div>

              {/* Message Details */}
              <div className="bg-white/90 rounded-lg p-4 border border-black/5 text-xs text-slate-800 whitespace-pre-line leading-relaxed shadow-xs">
                {evaluationResult.verdict_message}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
