"use client";

import React, { useState } from "react";
import { CheckSquare, Square, Sparkles } from "lucide-react";

export interface ClarifyOption {
  value: string;
  label: string;
  hint?: string;
}

export interface ClarifyGroup {
  key: string;
  label: string;
  short: string;
  multi: boolean;
  required: boolean;
  options: ClarifyOption[];
}

export interface ClarifyFormSpec {
  groups: ClarifyGroup[];
}

// ตัวเลือกช่องทางสำหรับข้อความเก่าที่ backend ยังไม่ได้ส่งฟอร์มมา
export const FALLBACK_CHANNEL_FORM: ClarifyFormSpec = {
  groups: [
    {
      key: "channel",
      label: "ช่องทางที่จะยื่นคำขอ",
      short: "ช่องทาง",
      multi: false,
      required: true,
      options: [
        { value: "paper", label: "ยื่นแบบกระดาษ ณ สำนักงานสรรพากรพื้นที่ (ฉบับที่ 57)" },
        { value: "internet", label: "ยื่นผ่านอินเทอร์เน็ต www.rd.go.th (ฉบับที่ 159)" },
        { value: "dbd", label: "ยื่นพร้อมจดทะเบียนจัดตั้งนิติบุคคลผ่าน DBD (ฉบับที่ 234)" },
      ],
    },
  ],
};

/** แปลงสิ่งที่เลือกเป็นข้อความตอบกลับ — กลุ่มเดียวส่ง label ตรงๆ หลายกลุ่มใส่ชื่อกลุ่มนำหน้า */
export function formReply(spec: ClarifyFormSpec, picked: Record<string, string[]>): string {
  const filled = spec.groups.filter((g) => (picked[g.key] || []).length > 0);
  const labels = (g: ClarifyGroup) =>
    g.options.filter((o) => picked[g.key].includes(o.value)).map((o) => o.label);
  if (spec.groups.length === 1 && filled.length === 1) return labels(filled[0]).join(", ");
  return filled.map((g) => `${g.short}: ${labels(g).join(", ")}`).join(" · ");
}

export default function ClarifyForm({
  spec,
  disabled,
  onSubmit,
}: {
  spec: ClarifyFormSpec;
  disabled?: boolean;
  onSubmit: (reply: string) => void;
}) {
  const [picked, setPicked] = useState<Record<string, string[]>>({});
  const [sent, setSent] = useState<string | null>(null);

  const toggle = (g: ClarifyGroup, value: string) => {
    if (sent) return;
    setPicked((prev) => {
      const cur = prev[g.key] || [];
      const next = cur.includes(value)
        ? cur.filter((v) => v !== value)
        : g.multi
          ? [...cur, value]
          : [value];
      return { ...prev, [g.key]: next };
    });
  };

  const ready = spec.groups.every((g) => !g.required || (picked[g.key] || []).length > 0);

  const submit = () => {
    if (!ready || sent || disabled) return;
    const reply = formReply(spec, picked);
    setSent(reply);
    onSubmit(reply);
  };

  return (
    <div className="mt-3 pt-3 border-t border-slate-100 space-y-3">
      <div className="text-[11.5px] font-bold text-blue-800 flex items-center gap-1.5">
        <Sparkles className="w-4 h-4 text-blue-600" />
        <span>กรุณาเลือกข้อมูลแล้วกด &quot;ยืนยัน&quot;</span>
      </div>
      {spec.groups.map((g) => (
        <fieldset key={g.key} className="space-y-1.5" disabled={!!sent}>
          <legend className="text-xs font-semibold text-slate-700 mb-1">
            {g.label}
            {g.required ? <span className="text-rose-600"> *</span> : null}
            {!g.multi && <span className="font-normal text-slate-400"> (เลือก 1 ข้อ)</span>}
          </legend>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
            {g.options.map((o) => {
              const on = (picked[g.key] || []).includes(o.value);
              return (
                <label
                  key={o.value}
                  className={`relative flex items-start gap-2 p-2 rounded-lg border text-left transition ${
                    sent ? "cursor-default" : "cursor-pointer"
                  } ${on ? "bg-blue-50 border-blue-400" : "bg-white border-slate-200 hover:bg-slate-50"}`}
                >
                  {/* input ซ่อนต้องอยู่ในกรอบ label (relative) — ไม่งั้นตอนได้ focus เบราว์เซอร์จะเลื่อนคอลัมน์แชททั้งคอลัมน์ขึ้นไป */}
                  <input
                    type="checkbox"
                    className="absolute inset-0 opacity-0 w-full h-full m-0 cursor-pointer"
                    checked={on}
                    onChange={() => toggle(g, o.value)}
                  />
                  {on ? (
                    <CheckSquare className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                  ) : (
                    <Square className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
                  )}
                  <span className="min-w-0">
                    <span className="block text-xs font-medium text-slate-800">{o.label}</span>
                    {o.hint && <span className="block text-[10.5px] text-slate-500">{o.hint}</span>}
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>
      ))}
      {sent ? (
        <div className="text-[11px] text-slate-500">ส่งข้อมูลแล้ว: {sent}</div>
      ) : (
        <button
          onClick={submit}
          disabled={!ready || disabled}
          className="px-4 py-1.5 rounded-lg text-xs font-bold text-white bg-blue-600 hover:bg-blue-500 disabled:bg-slate-300 disabled:cursor-not-allowed transition"
        >
          ยืนยัน
        </button>
      )}
    </div>
  );
}
