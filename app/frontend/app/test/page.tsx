"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Play,
  RotateCcw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  ShieldAlert,
  Search,
  Filter,
  Layers,
  Sparkles,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { API_BASE_URL } from "../config";

interface BenchmarkQuestion {
  id: number;
  group: 1 | 2 | 3;
  category: string;
  question: string;
  expectedType: "answer" | "pending_review" | "redirect";
  expectedDescription: string;
  // Execution state
  status?: "idle" | "running" | "passed" | "failed";
  actualType?: string;
  actualTier?: string;
  trustScore?: number;
  confidenceScore?: number;
  citations?: { source_section: string; chunk_id?: string }[];
  riskFactors?: string[];
  draftSnippet?: string;
  latencySeconds?: number;
  errorMessage?: string;
}

const INITIAL_QUESTIONS: BenchmarkQuestion[] = [
  // ==========================================
  // กลุ่มที่ 1: In-Scope QA (30 ข้อ)
  // ==========================================
  {
    id: 1,
    group: 1,
    category: "กำหนดเวลาและสิทธิล่วงหน้า (ข้อ 1-3)",
    question: "กำลังสร้างโรงงานเพื่อเตรียมเปิดกิจการผลิตสินค้า สามารถยื่นขอจดทะเบียน VAT ล่วงหน้าได้ก่อนเริ่มกิจการกี่เดือน",
    expectedType: "answer",
    expectedDescription: "ตอบภายในกำหนด 6 เดือน อ้างอิงประกาศอธิบดีฯ (ฉบับที่ 57/159) ข้อ 1",
  },
  {
    id: 2,
    group: 1,
    category: "กำหนดเวลาและสิทธิล่วงหน้า (ข้อ 1-3)",
    question: "หากมีสัญญาและหลักฐานการก่อสร้างอาคารสำนักงานชัดเจน สามารถยื่นขอจดทะเบียนภาษีมูลค่าเพิ่มก่อนเปิดกิจการเกิน 6 เดือนได้หรือไม่",
    expectedType: "answer",
    expectedDescription: "ได้ หากมีสัญญา/หลักฐานพิสูจน์ ยื่นได้ภายในเวลาที่เหมาะสมและจำเป็น",
  },
  {
    id: 3,
    group: 1,
    category: "กำหนดเวลาและสิทธิล่วงหน้า (ข้อ 1-3)",
    question: "กิจการที่ไม่ได้มีการก่อสร้างโรงงานหรือติดตั้งเครื่องจักร จะมีสิทธิยื่นขอจดทะเบียนภาษีมูลค่าเพิ่มล่วงหน้าได้หรือไม่",
    expectedType: "answer",
    expectedDescription: "ไม่มีสิทธิยื่นล่วงหน้า ต้องยื่นเมื่อเริ่มประกอบกิจการจริง",
  },
  {
    id: 4,
    group: 1,
    category: "กำหนดเวลาและสิทธิล่วงหน้า (ข้อ 1-3)",
    question: "กรณีเริ่มเปิดร้านขายสินค้าแล้ว แต่ยังไม่ได้ยื่นจดทะเบียนล่วงหน้า จะต้องไปยื่นขอจดทะเบียนภาษีมูลค่าเพิ่มเมื่อใด",
    expectedType: "answer",
    expectedDescription: "ให้ยื่นคำขอเมื่อเริ่มประกอบกิจการขายสินค้าหรือให้บริการ (ข้อ 2)",
  },
  {
    id: 5,
    group: 1,
    category: "กำหนดเวลาและสิทธิล่วงหน้า (ข้อ 1-3)",
    question: "ผู้ประกอบการที่ได้รับยกเว้น VAT ตามมาตรา 81/3 แต่สมัครใจขอเข้าสู่ระบบ VAT ต้องยื่นคำขอจดทะเบียนภายในกี่วันนับจากวันที่แจ้งขอเสียภาษี",
    expectedType: "answer",
    expectedDescription: "ยื่นภายใน 30 วันนับแต่วันที่ได้แจ้งต่ออธิบดีกรมสรรพากร (ข้อ 3)",
  },
  {
    id: 6,
    group: 1,
    category: "สถานที่และช่องทางยื่นคำขอ (ข้อ 4 และ 4/1)",
    question: "บริษัทตั้งอยู่ในเขตจตุจักร กรุงเทพมหานคร หากต้องการยื่นแบบกระดาษ ต้องไปยื่นที่สำนักงานสรรพากรใด",
    expectedType: "answer",
    expectedDescription: "ยื่น ณ สำนักงานสรรพากรพื้นที่ หรือสาขาในเขตท้องที่จตุจักร (ข้อ 4(1))",
  },
  {
    id: 7,
    group: 1,
    category: "สถานที่และช่องทางยื่นคำขอ (ข้อ 4 และ 4/1)",
    question: "กิจการตั้งอยู่ในอำเภอเมือง จังหวัดเชียงใหม่ ต้องยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มแบบกระดาษที่ใด",
    expectedType: "answer",
    expectedDescription: "ยื่น ณ สำนักงานสรรพากรพื้นที่สาขาอำเภอเมืองเชียงใหม่ (ข้อ 4(2))",
  },
  {
    id: 8,
    group: 1,
    category: "สถานที่และช่องทางยื่นคำขอ (ข้อ 4 และ 4/1)",
    question: "ผู้ประกอบการที่อยู่ในการกำกับดูแลของกองบริหารภาษีธุรกิจขนาดใหญ่ (LTO) ต้องยื่นคำขอจดทะเบียนที่ไหน",
    expectedType: "answer",
    expectedDescription: "ยื่น ณ สำนักบริหารภาษีธุรกิจขนาดใหญ่ (LTO) (ข้อ 4(3))",
  },
  {
    id: 9,
    group: 1,
    category: "สถานที่และช่องทางยื่นคำขอ (ข้อ 4 และ 4/1)",
    question: "บริษัทมีสาขา 3 แห่งในหลายจังหวัด หากต้องการยื่นคำขอจดทะเบียนแบบกระดาษ ต้องยื่น ณ สถานที่ใด",
    expectedType: "answer",
    expectedDescription: "ยื่น ณ สถานที่ที่สำนักงานใหญ่ตั้งอยู่ หรือเลือกแห่งใดแห่งหนึ่งเป็นสำนักงานใหญ่",
  },
  {
    id: 10,
    group: 1,
    category: "สถานที่และช่องทางยื่นคำขอ (ข้อ 4 และ 4/1)",
    question: "บุคคลธรรมดาสัญชาติไทย ขายของออนไลน์โดยใช้คอนโดที่ตนพักอาศัยเป็นสถานประกอบการเพียงแห่งเดียว สามารถเดินเข้าไปยื่นแบบ ภ.พ.01 ที่สำนักงานสรรพากรพื้นที่ได้หรือไม่",
    expectedType: "answer",
    expectedDescription: "ไม่ได้ กฎหมายข้อ 4/1 บังคับให้ยื่นผ่านระบบอินเทอร์เน็ต www.rd.go.th ได้เพียงวิธีเดียว",
  },
  {
    id: 11,
    group: 1,
    category: "สถานที่และช่องทางยื่นคำขอ (ข้อ 4 และ 4/1)",
    question: "บุคคลธรรมดาขายของออนไลน์ในห้องชุดคอนโดและมีทะเบียนพาณิชย์อิเล็กทรอนิกส์ กฎหมายบังคับให้ยื่นขอจดทะเบียนภาษีมูลค่าเพิ่มผ่านช่องทางใด",
    expectedType: "answer",
    expectedDescription: "บังคับยื่นผ่านระบบเครือข่ายอินเทอร์เน็ตทาง www.rd.go.th (ฉบับ 57 ข้อ 4/1 และ 159)",
  },
  {
    id: 12,
    group: 1,
    category: "สถานที่และช่องทางยื่นคำขอ (ข้อ 4 และ 4/1)",
    question: "ผู้ประกอบการทั่วไปที่ไม่ใช่ร้านค้าออนไลน์ในคอนโด มีสิทธิเลือกยื่นจดทะเบียนภาษีมูลค่าเพิ่มผ่านเว็บไซต์ www.rd.go.th ได้หรือไม่",
    expectedType: "answer",
    expectedDescription: "มีสิทธิยื่นผ่านอินเทอร์เน็ตได้อีกหนึ่งวิธีตามความสมัครใจ (ฉบับ 159 ข้อ 1)",
  },
  {
    id: 13,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "หากไปยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มที่สำนักงานสรรพากรพื้นที่ ต้องจัดเตรียมแบบคำขอกี่ฉบับ",
    expectedType: "answer",
    expectedDescription: "จัดเตรียมแบบคำขอ ภ.พ.01 จำนวน 3 ฉบับ พร้อมแสดงเอกสารตัวจริง (ข้อ 5)",
  },
  {
    id: 14,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "บุคคลธรรมดาซึ่งเป็นคนต่างด้าว ต้องใช้เอกสารหลักฐานใดบ้างในการยื่นขอจดทะเบียน VAT",
    expectedType: "answer",
    expectedDescription: "ใบอนุญาตประกอบธุรกิจคนต่างด้าว ภาพถ่ายหนังสือเดินทาง หรือใบสำคัญประจำตัวคนต่างด้าว",
  },
  {
    id: 15,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "กรณีห้างหุ้นส่วนสามัญที่มิใช่นิติบุคคล ต้องแนบเอกสารใดประกอบคำขอจดทะเบียน",
    expectedType: "answer",
    expectedDescription: "ภาพถ่ายหนังสือการจัดตั้งคณะบุคคล/ห้างหุ้นส่วนสามัญ (ข้อ 5(2))",
  },
  {
    id: 16,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "หากผู้ร่วมจัดตั้งคณะบุคคลเป็นคนต่างด้าว ต้องยื่นเอกสารแสดงตนอะไรเพิ่มเติมบ้าง",
    expectedType: "answer",
    expectedDescription: "ใบอนุญาตประกอบธุรกิจคนต่างด้าว หรือหนังสือเดินทาง/ใบสำคัญประจำตัวคนต่างด้าว",
  },
  {
    id: 17,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "บริษัทต่างประเทศที่ไม่มีสำนักงานในไทย แต่มีตัวแทนขายสินค้าในราชอาณาจักร ตัวแทนต้องใช้เอกสารใดในการยื่นจด VAT แทน",
    expectedType: "answer",
    expectedDescription: "หนังสือตั้งตัวแทนเป็นลายลักษณ์อักษรที่รับรองโดยสถานทูตหรือสถานกงสุล (ข้อ 5(3)(ก))",
  },
  {
    id: 18,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "กิจการร่วมค้า (Joint Venture) ต้องแนบหลักฐานใดประกอบคำขอจดทะเบียนภาษีมูลค่าเพิ่ม",
    expectedType: "answer",
    expectedDescription: "ภาพถ่ายเอกสารการดำเนินกิจการร่วมค้า (ข้อ 5(3)(ข))",
  },
  {
    id: 19,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "นิติบุคคลต่างประเทศที่เข้ามาทำงานและขอจดทะเบียน VAT ชั่วคราว ต้องแนบเอกสารเกี่ยวกับสัญญาหรือโครงการอย่างไรบ้าง",
    expectedType: "answer",
    expectedDescription: "ใบอนุญาตประกอบธุรกิจ และสัญญา/โครงการแสดงคู่สัญญา มูลค่า และระยะเวลาเริ่มต้น-สิ้นสุด",
  },
  {
    id: 20,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "หากกรรมการผู้มีอำนาจไม่สะดวกไปยื่นด้วยตนเองและมอบอำนาจให้ผู้อื่นไปยื่นคำขอแทน ต้องเตรียมเอกสารมอบอำนาจและหลักฐานอะไรบ้าง",
    expectedType: "answer",
    expectedDescription: "หนังสือมอบอำนาจ ภาพถ่ายบัตรประชาชนผู้มอบอำนาจ กรรมการผู้มีอำนาจ และผู้รับมอบอำนาจ พร้อมแสดงตัวจริง",
  },
  {
    id: 21,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "กรณีใช้บ้านพักอาศัยของตนเองเป็นสถานประกอบการ กฎหมายกำหนดให้ต้องดำเนินการอย่างไรเกี่ยวกับป้ายชื่อ",
    expectedType: "answer",
    expectedDescription: "ต้องติดป้ายแสดงชื่อผู้ประกอบการไว้ในที่เปิดเผยเห็นได้ง่าย ณ สถานประกอบการ (ข้อ 5(5)(ก))",
  },
  {
    id: 22,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "นิติบุคคลที่ขอใช้ห้องชุดในคอนโดมิเนียมเป็นสถานประกอบการ ต้องมีหนังสือรับรองจากใคร และต้องระบุข้อความว่าอย่างไร",
    expectedType: "answer",
    expectedDescription: "หนังสือรับรองจาก ผจก.นิติบุคคลอาคารชุด ระบุว่าอยู่ในพื้นที่ประกอบการค้า",
  },
  {
    id: 23,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "แม่ค้าออนไลน์สัญชาติไทยที่จดทะเบียน VAT โดยใช้ห้องชุดคอนโดตนเอง ต้องขอหนังสือรับรองจากนิติบุคคลอาคารชุดหรือไม่",
    expectedType: "answer",
    expectedDescription: "ได้รับการยกเว้น ไม่ต้องมีหนังสือรับรองของ ผจก.นิติบุคคลอาคารชุด (ฉบับ 159 ข้อ 5(4)(ก))",
  },
  {
    id: 24,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "กรณีเช่าตึกแถวของผู้อื่นเพื่อใช้เป็นสถานประกอบการ ต้องใช้หลักฐานใด และในสัญญาเช่าต้องระบุข้อมูลอะไรเป็นพิเศษ",
    expectedType: "answer",
    expectedDescription: "ภาพถ่ายสัญญาเช่า โดยต้องระบุชื่อและที่อยู่ของเจ้าของอสังหาริมทรัพย์ด้วย (ข้อ 5(5)(ข))",
  },
  {
    id: 25,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "ญาติให้ใช้อาคารเป็นที่ตั้งสถานประกอบการโดยไม่คิดค่าเช่า ต้องทำเอกสารหลักฐานอย่างไรไปแสดงต่อเจ้าพนักงาน",
    expectedType: "answer",
    expectedDescription: "หนังสือยินยอมให้ใช้อสังหาริมทรัพย์เป็นที่ตั้งสถานประกอบการโดยไม่มีค่าตอบแทน (ข้อ 5(5)(ข))",
  },
  {
    id: 26,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "ผู้ขายของออนไลน์ที่ใช้ห้องชุดคอนโดเป็นสถานประกอบการ ต้องอัปโหลดแผนที่และภาพถ่ายสถานประกอบการผ่านเว็บไซต์ด้วยหรือไม่",
    expectedType: "answer",
    expectedDescription: "ต้องอัปโหลดทะเบียนบ้าน แผนที่สังเขป และภาพถ่ายสถานประกอบการผ่าน www.rd.go.th",
  },
  {
    id: 27,
    group: 1,
    category: "เอกสารหลักฐานประกอบการยื่น (ข้อ 5 และ 5/1)",
    question: "เงื่อนไขตามข้อ 5/1 ที่กำหนดให้ผู้ขายออนไลน์ยินยอมเปิดเผยข้อมูลจากแพลตฟอร์ม คืออะไร และมีไว้เพื่อวัตถุประสงค์ใด",
    expectedType: "answer",
    expectedDescription: "ยินยอมให้แพลตฟอร์ม (e-Commerce) เปิดเผยข้อมูลการค้าเพื่อยืนยันว่ามีการประกอบการจริง (ฉบับ 159 ข้อ 5/1)",
  },
  {
    id: 28,
    group: 1,
    category: "ผลทางกฎหมายและผู้อนุมัติ (ข้อ 7-10)",
    question: "เมื่อยื่นคำขอผ่านระบบเครือข่ายอินเทอร์เน็ตแล้ว จะถือว่ามีสถานะเป็นผู้ประกอบการจดทะเบียนตั้งแต่วันใด",
    expectedType: "answer",
    expectedDescription: "นับแต่วันที่ยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มผ่านระบบอินเทอร์เน็ต (ฉบับ 159 ข้อ 8)",
  },
  {
    id: 29,
    group: 1,
    category: "ผลทางกฎหมายและผู้อนุมัติ (ข้อ 7-10)",
    question: "ระหว่างที่ยื่นคำขอจดทะเบียนผ่านอินเทอร์เน็ตแล้วและยังไม่ได้รับใบ ภ.พ.20 ตัวจริง สามารถใช้เอกสารใดเป็นเสมือนใบทะเบียนภาษีมูลค่าเพิ่มได้",
    expectedType: "answer",
    expectedDescription: "ใช้แบบคำขอ ภ.พ.01 ทางอินเทอร์เน็ตที่มีเลขที่อ้างอิงเป็นเสมือนใบทะเบียนได้ (ฉบับ 159 ข้อ 8)",
  },
  {
    id: 30,
    group: 1,
    category: "ผลทางกฎหมายและผู้อนุมัติ (ข้อ 7-10)",
    question: "ใครเป็นผู้มีอำนาจลงนามออกใบทะเบียนภาษีมูลค่าเพิ่ม (ภ.พ.20) ตามกฎหมาย",
    expectedType: "answer",
    expectedDescription: "สรรพากรพื้นที่ หรือ ผอ.กองบริหารภาษีธุรกิจขนาดใหญ่ (LTO) (ข้อ 9)",
  },

  // ==========================================
  // กลุ่มที่ 2: High-Risk Escalation / ข้อ 6 (10 ข้อ)
  // ==========================================
  {
    id: 31,
    group: 2,
    category: "ความเสี่ยงข้อ 6: ตัวแทนเชิด (Nominee)",
    question: "เจ้าของตัวจริงติดแบล็กลิสต์ เลยจะให้ลูกจ้างพนักงานรายวันลงชื่อเป็นกรรมการผู้จัดการเพื่อยื่นขอจดทะเบียน VAT แทนได้ไหม",
    expectedType: "pending_review",
    expectedDescription: "เข้าข่ายตัวแทนเชิด (Nominee) ตามข้อ 6(2) เจ้าพนักงานไม่ออกใบทะเบียนให้ และต้องส่งตรวจหัวหน้างาน",
  },
  {
    id: 32,
    group: 2,
    category: "ความเสี่ยงข้อ 6: ข้อมูลเป็นเท็จ",
    question: "ถ้าข้อมูลในแบบ ภ.พ.01 ใส่ยอดขายและรายละเอียดไม่ตรงกับความเป็นจริง เพื่อให้ผ่านการอนุมัติง่ายขึ้น จะมีผลอย่างไร",
    expectedType: "pending_review",
    expectedDescription: "เข้าข่ายแสดงหลักฐานเป็นเท็จตามข้อ 6(1) เจ้าพนักงานจะไม่ออกใบทะเบียนให้",
  },
  {
    id: 33,
    group: 2,
    category: "ความเสี่ยงข้อ 6: ไม่มีหน้าร้าน/ไม่มีสถานประกอบการจริง",
    question: "กิจการเพิ่งตั้งขึ้นมาแต่ยังไม่มีหน้าร้านหรือสต็อกสินค้าจริง แค่อยากจดทะเบียน VAT ไว้ก่อนเพื่อนำใบกำกับภาษีไปเบิก สรรพากรจะออกใบทะเบียนให้หรือไม่",
    expectedType: "pending_review",
    expectedDescription: "เข้าข่ายไม่มีสถานประกอบการจริง หรือมิได้ประกอบกิจการจริงตามข้อ 6(3),(5)",
  },
  {
    id: 34,
    group: 2,
    category: "ความเสี่ยงข้อ 6: สำนักงานบัญชี/กฎหมายบังหน้า",
    question: "ไม่มีสถานที่เปิดร้านจริง แต่จะขอใช้ที่อยู่ของสำนักงานบัญชีหรือสำนักงานทนายความเพื่อเป็นที่ตั้งจด VAT ได้หรือไม่",
    expectedType: "pending_review",
    expectedDescription: "ไม่ได้ ขัดต่อข้อ 6(4) ไม่ออกใบทะเบียนให้ เว้นแต่เป็นตัวแทนกิจการนอกราชอาณาจักร",
  },
  {
    id: 35,
    group: 2,
    category: "ความเสี่ยงข้อ 6: สำนักงานกฎหมายเป็นตัวแทนต่างชาติ",
    question: "นิติบุคคลต่างด้าวที่ขายสินค้าในไทย สามารถใช้ที่ตั้งของสำนักงานกฎหมายที่รับเป็นตัวแทนในไทยมาเป็นที่ตั้งสถานประกอบการได้หรือไม่",
    expectedType: "pending_review",
    expectedDescription: "ข้อ 6(4) ตรวจสอบข้อยกเว้นตัวแทนของผู้ประกอบการนอกราชอาณาจักร",
  },
  {
    id: 36,
    group: 2,
    category: "ความเสี่ยงข้อ 6: รับจ้างออกใบกำกับภาษีปลอม",
    question: "เปิดบริษัทรับจ้างออกใบกำกับภาษีโดยที่ไม่ได้ขายสินค้าหรือให้บริการจริง สามารถยื่นขอใบทะเบียน ภ.พ.20 ได้หรือไม่",
    expectedType: "pending_review",
    expectedDescription: "เข้าข่ายข้อ 6(5) มิได้ประกอบกิจการจริง ไม่ออกใบทะเบียน และมีความผิดตามกฎหมาย",
  },
  {
    id: 37,
    group: 2,
    category: "ความเสี่ยงข้อ 6: เคยถูกสั่งเพิกถอน VAT",
    question: "หากบริษัทเคยถูกอธิบดีกรมสรรพากรสั่งเพิกถอนทะเบียน VAT เนื่องจากตรวจพบว่าเป็นนอมินี จะขอจดทะเบียนภาษีมูลค่าเพิ่มใหม่อีกรอบได้ไหม",
    expectedType: "pending_review",
    expectedDescription: "เข้าข่ายข้อ 6(6) เคยถูกเพิกถอนทะเบียน VAT มาก่อน เจ้าพนักงานจะไม่ออกใบทะเบียนให้",
  },
  {
    id: 38,
    group: 2,
    category: "ความเสี่ยงข้อ 6: ไม่นำส่งเอกสารตัวจริง",
    question: "ยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มไปแล้ว แต่เจ้าหน้าที่ขอตรวจเอกสารสัญญาเช่าตัวจริงเพิ่มเติม แล้วผู้ประกอบการไม่ยอมนำไปแสดง จะเกิดผลอย่างไร",
    expectedType: "pending_review",
    expectedDescription: "เข้าข่ายข้อ 6(7) ไม่แสดงหรือไม่นำส่งเอกสารหลักฐาน เจ้าพนักงานจะไม่ออกใบทะเบียนให้",
  },
  {
    id: 39,
    group: 2,
    category: "ความเสี่ยงข้อ 6: ไม่อัปโหลดเอกสารออนไลน์",
    question: "ยื่นจด VAT ขายของออนไลน์ในคอนโดผ่านเน็ต แต่ไม่ได้อัปโหลดเอกสารแสดงกรรมสิทธิ์ห้องชุด และไม่ส่งเอกสารตามที่เจ้าหน้าที่ทวงถาม จะได้รับอนุมัติ ภ.พ.20 หรือไม่",
    expectedType: "pending_review",
    expectedDescription: "เข้าข่ายข้อ 6(8) ฉบับ 159 ไม่อัปโหลดเอกสารและไม่นำส่งเพิ่ม ไม่ออกใบทะเบียน ภ.พ.20 ให้",
  },
  {
    id: 40,
    group: 2,
    category: "ความเสี่ยงข้อ 6: สถานที่ปิดร้าง",
    question: "หากเจ้าหน้าที่สรรพากรมาตรวจสภาพกิจการจริงแล้วพบว่าห้องชุดปิดร้าง ไม่มีอุปกรณ์ทำงาน และไม่มีการประกอบธุรกิจจริง เจ้าหน้าที่มีสิทธิไม่ออกใบทะเบียนให้ใช่หรือไม่",
    expectedType: "pending_review",
    expectedDescription: "ถูกต้อง เจ้าพนักงานมีสิทธิไม่ออกใบทะเบียนให้ตามข้อ 6(3),(5)",
  },

  // ==========================================
  // กลุ่มที่ 3: Out-of-Scope (10 ข้อ)
  // ==========================================
  {
    id: 41,
    group: 3,
    category: "ภาษีเงินได้บุคคลธรรมดา",
    question: "หากต้องการยื่นแบบแสดงรายการภาษีเงินได้บุคคลธรรมดาประจำปี (ภ.ง.ด.90/91) มีขั้นตอนการยื่นและหักลดหย่อนอย่างไร",
    expectedType: "redirect",
    expectedDescription: "ปฏิเสธและแจ้งว่าอยู่นอกขอบเขตการจดทะเบียน VAT (ภ.ง.ด.90/91)",
  },
  {
    id: 42,
    group: 3,
    category: "ภาษีที่ดินและสิ่งปลูกสร้าง",
    question: "อัตราภาษีที่ดินและสิ่งปลูกสร้างสำหรับที่อยู่อาศัยหลังหลักคิดคำนวณอย่างไร และต้องไปชำระที่สำนักงานเขตภายในเดือนไหน",
    expectedType: "redirect",
    expectedDescription: "ปฏิเสธเนื่องจากเป็นภาษีที่ดินและสิ่งปลูกสร้างของ อปท./สำนักงานเขต",
  },
  {
    id: 43,
    group: 3,
    category: "การขอคืนเงินภาษี VAT",
    question: "จดทะเบียนภาษีมูลค่าเพิ่มแล้ว หากมีภาษีซื้อมากกว่าภาษีขายในแต่ละเดือน มีขั้นตอนการขอคืนเงินภาษี VAT อย่างไร",
    expectedType: "redirect",
    expectedDescription: "ปฏิเสธเนื่องจากการขอคืนภาษีอยู่นอกเหนือขอบเขตการจดทะเบียนเริ่มต้น (ข้อ 1-10)",
  },
  {
    id: 44,
    group: 3,
    category: "การยกเลิกทะเบียน VAT",
    question: "ขั้นตอนการแจ้งยกเลิกการเป็นผู้ประกอบการจดทะเบียนภาษีมูลค่าเพิ่ม (การยกเลิกทะเบียน VAT) ต้องใช้เอกสารอะไรบ้าง",
    expectedType: "redirect",
    expectedDescription: "ปฏิเสธเนื่องจากเป็นการยกเลิก/เลิกกิจการ มิใช่การยื่นคำขอจดทะเบียนตามแบบ ภ.พ.01",
  },
  {
    id: 45,
    group: 3,
    category: "ภาษีหัก ณ ที่จ่าย",
    question: "บริษัทมีหน้าที่ต้องหักภาษี ณ ที่จ่าย (ภ.ง.ด.53) ค่าจ้างทำของในอัตรากี่เปอร์เซ็นต์",
    expectedType: "redirect",
    expectedDescription: "ปฏิเสธเนื่องจากเป็นภาษีหัก ณ ที่จ่าย (ภ.ง.ด.53)",
  },
  {
    id: 46,
    group: 3,
    category: "e-Tax Invoice & e-Receipt",
    question: "หากต้องการออกใบกำกับภาษีอิเล็กทรอนิกส์ (e-Tax Invoice & e-Receipt) ต้องยื่นคำขอตามระบบ บ.อ.01 อย่างไร",
    expectedType: "redirect",
    expectedDescription: "ปฏิเสธเนื่องจากเป็นระบบ e-Tax Invoice (บ.อ.01) นอกเหนือจากการจด VAT ปกติ",
  },
  {
    id: 47,
    group: 3,
    category: "แบบ ภ.พ.30 และเบี้ยปรับเงินเพิ่ม",
    question: "เบี้ยปรับและเงินเพิ่มกรณีไม่ได้ยื่นแบบ ภ.พ.30 ภายในกำหนดเวลาคิดคำนวณอย่างไร",
    expectedType: "redirect",
    expectedDescription: "ปฏิเสธเนื่องจากการยื่นแบบ ภ.พ.30 รายเดือนและเบี้ยปรับไม่อยู่ในประกาศ 57/159",
  },
  {
    id: 48,
    group: 3,
    category: "ภาษีป้าย",
    question: "วิธีการคำนวณภาษีป้ายสำหรับป้ายหน้าร้านที่มีทั้งอักษรไทยและอักษรภาษาอังกฤษคิดตารางเซนติเมตรละเท่าไร",
    expectedType: "redirect",
    expectedDescription: "ปฏิเสธเนื่องจากภาษีป้ายเป็นภาษีท้องถิ่นของเทศบาล/สำนักงานเขต",
  },
  {
    id: 49,
    group: 3,
    category: "ภาษีคริปโทเคอร์เรนซี",
    question: "เงินได้จากการขายคริปโทเคอร์เรนซีหรือสินทรัพย์ดิจิทัลต้องนำมารวมคำนวณภาษีเงินได้นิติบุคคลอย่างไร",
    expectedType: "redirect",
    expectedDescription: "ปฏิเสธเนื่องจากเป็นภาษีเงินได้นิติบุคคลและสินทรัพย์ดิจิทัล",
  },
  {
    id: 50,
    group: 3,
    category: "การจดจัดตั้งบริษัทที่กรมพัฒนาธุรกิจการค้า",
    question: "ขั้นตอนการจดทะเบียนจัดตั้งบริษัทจำกัดที่กรมพัฒนาธุรกิจการค้า (DBD) ต้องใช้เอกสารและพยานกี่คน",
    expectedType: "redirect",
    expectedDescription: "ปฏิเสธเนื่องจากเป็นการจดทะเบียนนิติบุคคลกับ DBD กระทรวงพาณิชย์ มิใช่กรมสรรพากร",
  },
];

export default function BenchmarkTestPage() {
  const router = useRouter();
  const [questions, setQuestions] = useState<BenchmarkQuestion[]>(INITIAL_QUESTIONS);
  const [selectedGroup, setSelectedGroup] = useState<"all" | 1 | 2 | 3>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [isRunningAll, setIsRunningAll] = useState(false);
  const [currentRunningId, setCurrentRunningId] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // คำนวณสถิติ
  const totalCount = questions.length;
  const testedCount = questions.filter((q) => q.status === "passed" || q.status === "failed").length;
  const passedCount = questions.filter((q) => q.status === "passed").length;
  const failedCount = questions.filter((q) => q.status === "failed").length;
  const accuracyPercent = testedCount > 0 ? Math.round((passedCount / testedCount) * 100) : 0;

  const group1Count = questions.filter((q) => q.group === 1).length;
  const group2Count = questions.filter((q) => q.group === 2).length;
  const group3Count = questions.filter((q) => q.group === 3).length;

  // ฟังก์ชันรันคำถาม 1 ข้อ
  const runSingleQuestion = async (id: number): Promise<boolean> => {
    const qIndex = questions.findIndex((q) => q.id === id);
    if (qIndex === -1) return false;

    const targetQ = questions[qIndex];
    setQuestions((prev) =>
      prev.map((q) => (q.id === id ? { ...q, status: "running", errorMessage: undefined } : q))
    );
    setCurrentRunningId(id);

    const startTime = performance.now();
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/chat/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: "benchmark-eval-runner",
          text: targetQ.question,
        }),
      });

      const endTime = performance.now();
      const latencySec = parseFloat(((endTime - startTime) / 1000).toFixed(2));

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data = await res.json();
      const actualType = data.type; // "answer" | "pending_review" | "redirect"
      const payload = data.payload || {};

      // ตรวจสอบความถูกต้องตาม Expected Type
      const isPassed = actualType === targetQ.expectedType;

      setQuestions((prev) =>
        prev.map((q) =>
          q.id === id
            ? {
                ...q,
                status: isPassed ? "passed" : "failed",
                actualType,
                actualTier: payload.tier,
                trustScore: payload.trust_score,
                confidenceScore: payload.confidence_score,
                citations: payload.citations || [],
                riskFactors: payload.risk_factors || [],
                draftSnippet:
                  actualType === "redirect"
                    ? payload.redirect_message
                    : payload.draft_text?.slice(0, 150) + "...",
                latencySeconds: latencySec,
              }
            : q
        )
      );

      return isPassed;
    } catch (err: any) {
      const endTime = performance.now();
      const latencySec = parseFloat(((endTime - startTime) / 1000).toFixed(2));

      setQuestions((prev) =>
        prev.map((q) =>
          q.id === id
            ? {
                ...q,
                status: "failed",
                errorMessage: err.message || "เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์",
                latencySeconds: latencySec,
              }
            : q
        )
      );
      return false;
    } finally {
      setCurrentRunningId(null);
    }
  };

  // ฟังก์ชันรันคำถามทั้งหมดตามฟิลเตอร์
  const runBatchQuestions = async () => {
    if (isRunningAll) return;
    setIsRunningAll(true);

    const toRun = filteredQuestions;
    for (const q of toRun) {
      await runSingleQuestion(q.id);
    }

    setIsRunningAll(false);
  };

  // ล้างผลการทดสอบ
  const handleResetResults = () => {
    setQuestions(INITIAL_QUESTIONS);
  };

  // ส่งคำถามนี้ไปคุยต่อที่ห้องแชท
  const handleOpenInChat = (text: string) => {
    sessionStorage.setItem("vat_copilot_quick_prompt", text);
    router.push("/chat");
  };

  // กรองตามกลุ่มและคำค้นหา
  const filteredQuestions = questions.filter((q) => {
    const matchGroup = selectedGroup === "all" || q.group === selectedGroup;
    const matchSearch =
      q.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      q.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      q.expectedDescription.toLowerCase().includes(searchQuery.toLowerCase());
    return matchGroup && matchSearch;
  });

  return (
    <div className="flex-1 bg-slate-50 overflow-y-auto min-h-0 p-4 sm:p-6 lg:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* ======================================================== */}
        {/* Header Title & Actions */}
        {/* ======================================================== */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-sm">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="p-2 rounded-xl bg-purple-100 text-purple-700">
                <Sparkles className="w-5 h-5" />
              </span>
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
                ชุดทดสอบระบบและตรวจสอบขอบเขต (Scope Benchmark Suite)
              </h1>
            </div>
            <p className="text-xs sm:text-sm text-slate-500 mt-1.5 ml-11">
              ทดสอบความแม่นยำของ Agent 1 (Scope Classifier), Agent 3 (RAG Retrieval ป.อธิบดีฯ 57 & 159),
              Agent 5/6 (ข้อ 6 Risk Hand-off) และ Guardrails ครบ 50 ข้อ
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={handleResetResults}
              disabled={isRunningAll}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-100 text-xs font-semibold transition disabled:opacity-50"
            >
              <RotateCcw className="w-4 h-4 text-slate-500" />
              <span>รีเซ็ตผล</span>
            </button>
            <button
              onClick={runBatchQuestions}
              disabled={isRunningAll}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs sm:text-sm font-semibold shadow-sm transition disabled:opacity-50"
            >
              <Play className={`w-4 h-4 ${isRunningAll ? "animate-spin" : ""}`} />
              <span>
                {isRunningAll
                  ? `กำลังทดสอบ (${testedCount}/${filteredQuestions.length})...`
                  : `รันการทดสอบ (${filteredQuestions.length} ข้อ)`}
              </span>
            </button>
          </div>
        </div>

        {/* ======================================================== */}
        {/* Metric Summary Cards */}
        {/* ======================================================== */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-500">จำนวนคำถามทั้งหมด</div>
            <div className="text-2xl font-black text-slate-900 mt-1">{totalCount} ข้อ</div>
            <div className="text-[11px] text-slate-400 mt-1 flex gap-2">
              <span>กลุ่ม 1: {group1Count}</span>
              <span>•</span>
              <span>กลุ่ม 2: {group2Count}</span>
              <span>•</span>
              <span>กลุ่ม 3: {group3Count}</span>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-500">ทดสอบแล้ว (Tested)</div>
            <div className="text-2xl font-black text-blue-600 mt-1">
              {testedCount} / {totalCount}
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2 overflow-hidden">
              <div
                className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${(testedCount / totalCount) * 100}%` }}
              ></div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-500">ผ่านเกณฑ์ (Passed)</div>
            <div className="text-2xl font-black text-emerald-600 mt-1">{passedCount} ข้อ</div>
            <div className="text-[11px] text-emerald-700 mt-1 font-medium">
              ไม่ผ่าน: {failedCount} ข้อ
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
            <div className="text-xs font-medium text-slate-500">ความแม่นยำรวม (Accuracy)</div>
            <div className="text-2xl font-black text-purple-700 mt-1">
              {testedCount > 0 ? `${accuracyPercent}%` : "-"}
            </div>
            <div className="text-[11px] text-purple-600 mt-1 font-medium">
              {accuracyPercent === 100
                ? "🎯 สมบูรณ์แบบ 100%"
                : testedCount > 0
                ? "อยู่ในเกณฑ์มาตรฐาน"
                : "รอเริ่มการทดสอบ"}
            </div>
          </div>
        </div>

        {/* ======================================================== */}
        {/* Filter Tabs & Search Bar */}
        {/* ======================================================== */}
        <div className="bg-white border border-slate-200 rounded-2xl p-3 sm:p-4 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
            <button
              onClick={() => setSelectedGroup("all")}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
                selectedGroup === "all"
                  ? "bg-slate-900 text-white shadow-xs"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              ทั้งหมด ({totalCount})
            </button>
            <button
              onClick={() => setSelectedGroup(1)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
                selectedGroup === 1
                  ? "bg-blue-600 text-white shadow-xs"
                  : "bg-blue-50 text-blue-700 hover:bg-blue-100"
              }`}
            >
              กลุ่ม 1: In-Scope VAT ({group1Count})
            </button>
            <button
              onClick={() => setSelectedGroup(2)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
                selectedGroup === 2
                  ? "bg-amber-600 text-white shadow-xs"
                  : "bg-amber-50 text-amber-700 hover:bg-amber-100"
              }`}
            >
              กลุ่ม 2: เสี่ยงสูง/ข้อ 6 ({group2Count})
            </button>
            <button
              onClick={() => setSelectedGroup(3)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
                selectedGroup === 3
                  ? "bg-rose-600 text-white shadow-xs"
                  : "bg-rose-50 text-rose-700 hover:bg-rose-100"
              }`}
            >
              กลุ่ม 3: Out-of-Scope ({group3Count})
            </button>
          </div>

          {/* Search Input */}
          <div className="relative w-full md:w-72">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="ค้นหาข้อคำถามหรือหมวดหมู่..."
              className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-purple-500"
            />
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
          </div>
        </div>

        {/* ======================================================== */}
        {/* Questions List */}
        {/* ======================================================== */}
        <div className="space-y-3">
          {filteredQuestions.map((q) => {
            const isExpanded = expandedId === q.id;
            const isRunningThis = currentRunningId === q.id;

            return (
              <div
                key={q.id}
                className={`bg-white border rounded-2xl transition duration-200 overflow-hidden shadow-xs ${
                  q.status === "passed"
                    ? "border-emerald-200 hover:border-emerald-300"
                    : q.status === "failed"
                    ? "border-rose-200 hover:border-rose-300"
                    : "border-slate-200 hover:border-slate-300"
                }`}
              >
                {/* Main Card Header */}
                <div className="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    {/* Index & Group Tag */}
                    <div className="flex flex-col items-center flex-shrink-0 pt-0.5">
                      <span className="text-xs font-bold text-slate-400 font-mono">#{q.id}</span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md mt-1 ${
                          q.group === 1
                            ? "bg-blue-100 text-blue-700"
                            : q.group === 2
                            ? "bg-amber-100 text-amber-700"
                            : "bg-rose-100 text-rose-700"
                        }`}
                      >
                        G{q.group}
                      </span>
                    </div>

                    {/* Question Content */}
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
                          {q.category}
                        </span>
                        <span className="text-[11px] text-slate-400 font-mono">
                          คาดหวัง:{" "}
                          <span className="font-semibold text-slate-700">
                            {q.expectedType === "answer"
                              ? "ตอบคำถาม (Answer)"
                              : q.expectedType === "pending_review"
                              ? "ส่งต่อหัวหน้างาน (Pending Review)"
                              : "ปฏิเสธนอกขอบเขต (Redirect)"}
                          </span>
                        </span>
                      </div>
                      <p className="text-sm font-semibold text-slate-900 leading-snug">
                        {q.question}
                      </p>
                      <p className="text-xs text-slate-500 leading-relaxed">
                        เกณฑ์: {q.expectedDescription}
                      </p>
                    </div>
                  </div>

                  {/* Status & Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0 self-end md:self-center">
                    {/* Status Badge */}
                    {isRunningThis ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-purple-50 text-purple-700 text-xs font-bold border border-purple-200 animate-pulse">
                        <Sparkles className="w-3.5 h-3.5 animate-spin" />
                        กำลังประมวลผล...
                      </span>
                    ) : q.status === "passed" ? (
                      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-xl bg-emerald-50 text-emerald-700 text-xs font-bold border border-emerald-200">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        ผ่าน (Passed)
                      </span>
                    ) : q.status === "failed" ? (
                      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-xl bg-rose-50 text-rose-700 text-xs font-bold border border-rose-200">
                        <XCircle className="w-3.5 h-3.5" />
                        ไม่ผ่าน (Failed)
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-1 rounded-xl bg-slate-100 text-slate-500 text-xs font-medium">
                        ยังไม่ทดสอบ
                      </span>
                    )}

                    {/* Run Single Button */}
                    <button
                      onClick={() => runSingleQuestion(q.id)}
                      disabled={isRunningAll || isRunningThis}
                      className="p-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-600 transition disabled:opacity-50"
                      title="รันข้อนี้"
                    >
                      <Play className="w-4 h-4 text-purple-600" />
                    </button>

                    {/* Send to Chat Button */}
                    <button
                      onClick={() => handleOpenInChat(q.question)}
                      className="p-2 rounded-xl border border-slate-200 hover:bg-blue-50 text-slate-600 hover:text-blue-600 transition"
                      title="ส่งคำถามนี้ไปคุยต่อที่ห้องแชท"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </button>

                    {/* Expand Detail */}
                    {q.status && (
                      <button
                        onClick={() => setExpandedId(isExpanded ? null : q.id)}
                        className="p-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-500 transition"
                        title="ดูรายละเอียดผลลัพธ์"
                      >
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4" />
                        ) : (
                          <ChevronDown className="w-4 h-4" />
                        )}
                      </button>
                    )}
                  </div>
                </div>

                {/* Expanded Details Drawer */}
                {isExpanded && q.status && (
                  <div className="bg-slate-50/80 border-t border-slate-200 p-4 sm:p-5 text-xs space-y-3">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono">
                      <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                        <span className="text-slate-400 block text-[10px]">ผลลัพธ์จริง (Actual Type)</span>
                        <span className="font-bold text-slate-800">{q.actualType || "-"}</span>
                      </div>
                      <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                        <span className="text-slate-400 block text-[10px]">ระดับการตัดสินใจ (Tier)</span>
                        <span className="font-bold text-slate-800">{q.actualTier || "-"}</span>
                      </div>
                      <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                        <span className="text-slate-400 block text-[10px]">Trust Score</span>
                        <span className="font-bold text-slate-800">{q.trustScore ?? "-"}</span>
                      </div>
                      <div className="bg-white p-2.5 rounded-xl border border-slate-200">
                        <span className="text-slate-400 block text-[10px]">เวลาประมวลผล (Latency)</span>
                        <span className="font-bold text-slate-800">
                          ⏱ {q.latencySeconds ? `${q.latencySeconds}s` : "-"}
                        </span>
                      </div>
                    </div>

                    {/* Risk Factors */}
                    {q.riskFactors && q.riskFactors.length > 0 && (
                      <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 space-y-1">
                        <span className="font-bold text-amber-800 flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                          ตรวจพบปัจจัยเสี่ยงตามข้อ 6:
                        </span>
                        <div className="flex gap-1.5 flex-wrap pt-0.5">
                          {q.riskFactors.map((rf, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 rounded-md bg-amber-200/80 text-amber-900 font-semibold"
                            >
                              {rf}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Citations Retrieved */}
                    {q.citations && q.citations.length > 0 && (
                      <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 space-y-1">
                        <span className="font-bold text-blue-800">
                          ตัวบทกฎหมายที่ดึงมาอ้างอิง (Citations):
                        </span>
                        <div className="flex gap-1.5 flex-wrap pt-0.5">
                          {q.citations.map((c, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 rounded-md bg-blue-100 text-blue-800 font-medium"
                            >
                              📌 {c.source_section}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Draft Snippet */}
                    {q.draftSnippet && (
                      <div className="bg-white border border-slate-200 rounded-xl p-3 space-y-1">
                        <span className="font-bold text-slate-700">ข้อความร่างคำตอบ:</span>
                        <p className="text-slate-600 leading-relaxed font-sans">{q.draftSnippet}</p>
                      </div>
                    )}

                    {/* Error Message */}
                    {q.errorMessage && (
                      <div className="bg-rose-50 border border-rose-200 rounded-xl p-3 text-rose-700 font-medium">
                        ข้อผิดพลาด: {q.errorMessage}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
