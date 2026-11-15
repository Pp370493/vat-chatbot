"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Send,
  Bot,
  User,
  ShieldAlert,
  ShieldCheck,
  Clock,
  BookOpen,
  FileText,
  Search,
  PlusCircle,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  History,
  Lock,
  CheckSquare,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import Link from "next/link";
import ChecklistAssistantModal from "../components/ChecklistAssistantModal";
import { API_BASE_URL } from "../config";

interface Citation {
  text_span: string;
  source_section: string;
}

interface LawSection {
  id: string;
  section: string;
  title: string;
  content: string;
}

interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  query_id?: string;
  type?: "answer" | "pending_review" | "redirect" | "clarification" | "form_assist";
  citations?: Citation[];
  trust_score?: number;
  confidence_score?: number;
  tier?: string;
  risk_factors?: string[];
  escalation_id?: string;
  is_clarification?: boolean;
  clarification_type?: string;
  relevant_articles?: LawSection[];
}

interface RecentInquiry {
  query_id: string;
  conversation_id: string;
  raw_text: string;
  answer: string;
  status: string;
  created_at: string;
}

export default function ChatPage() {
  const { user } = useAuth();

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: "สวัสดีค่ะ ดิฉันคือผู้ช่วย AI สำหรับเจ้าหน้าที่กรมสรรพากร ในการตอบข้อหารือและตรวจสอบหลักเกณฑ์การจดทะเบียนภาษีมูลค่าเพิ่ม (VAT) อ้างอิงตามประกาศอธิบดีกรมสรรพากรทั้ง 10 ฉบับ (ฉบับที่ 57, 74, 139, 159, 165, 214, 215, 234, 245, 246) และประมวลรัษฎากร คุณสามารถพิมพ์ข้อหารือเพื่อเริ่มตรวจสอบได้เลยค่ะ",
      type: "answer",
      tier: "auto_answer",
      trust_score: 0.95,
    },
  ]);

  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string>("");
  const [activeCitation, setActiveCitation] = useState<string | null>(null);
  const [lawSearchQuery, setLawSearchQuery] = useState("");
  const [loadingSeconds, setLoadingSeconds] = useState(0);

  // ตัวบทเฉพาะที่เกี่ยวข้องกับคำตอบปัจจุบัน (ข้อ 2: แสดงเฉพาะที่เกี่ยวข้อง อันที่ไม่เกี่ยวข้องไม่ต้องแสดง)
  const [activeRelevantArticles, setActiveRelevantArticles] = useState<LawSection[]>([]);
  const [allArticles, setAllArticles] = useState<LawSection[]>([]);

  // Recent Inquiries for Logged-in User (ข้อ 2)
  const [recentInquiries, setRecentInquiries] = useState<RecentInquiry[]>([]);
  const [isRecentLoading, setIsRecentLoading] = useState(false);

  // Confirm Dialog State (ข้อ 3)
  const [showConfirmNewTopic, setShowConfirmNewTopic] = useState(false);

  // Agent 7: Checklist Assistant Modal State
  const [showChecklistModal, setShowChecklistModal] = useState(false);

  const handlePostSummaryToChat = (summaryText: string) => {
    const summaryMsg: Message = {
      id: Date.now().toString(),
      sender: "assistant",
      text: summaryText,
      type: "answer",
      tier: "auto_answer",
      trust_score: 1.0,
      citations: [
        { text_span: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5", source_section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5" },
        { text_span: "ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5", source_section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5" },
        { text_span: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 6", source_section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 6" },
      ],
    };
    setMessages((prev) => [...prev, summaryMsg]);
    fetchRecentInquiries();
  };

  const inputRef = useRef<HTMLInputElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Fetch recent inquiries for current user
  const fetchRecentInquiries = async () => {
    setIsRecentLoading(true);
    try {
      const url = user?.user_id
        ? `${API_BASE_URL}/api/v1/chat/inquiries/recent?user_id=${user.user_id}&limit=5`
        : `${API_BASE_URL}/api/v1/chat/inquiries/recent?limit=5`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setRecentInquiries(data);
      }
    } catch (e) {
      console.error("Failed to load recent inquiries", e);
    } finally {
      setIsRecentLoading(false);
    }
  };

  useEffect(() => {
    fetchRecentInquiries();
  }, [user]);

  // Timer while loading to show live local CPU elapsed seconds
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isLoading) {
      setLoadingSeconds(0);
      interval = setInterval(() => {
        setLoadingSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isLoading]);

  // Auto focus on input when page mounts & handle quick prompt from Benchmark Test page
  useEffect(() => {
    inputRef.current?.focus();
    const quickPrompt = sessionStorage.getItem("vat_copilot_quick_prompt");
    if (quickPrompt) {
      setInputText(quickPrompt);
      sessionStorage.removeItem("vat_copilot_quick_prompt");
    }
  }, []);

  // Smooth scroll strictly inside chat container without moving window
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages, isLoading]);

  // ข้อ 3: เปิด Confirm Dialog ก่อนเริ่มข้อหารือใหม่
  const handleOpenNewTopicDialog = () => {
    // ถ้าเพิ่งเปิดหน้าเว็บและยังไม่ได้ถามอะไร สามารถเคลียร์ได้เลยไม่ต้องถาม
    if (messages.length <= 1 && !inputText) {
      executeResetChat();
      return;
    }
    setShowConfirmNewTopic(true);
  };

  // ดำเนินการล้างแชทจริงหลังจากกดยืนยันใน Confirm Dialog
  const executeResetChat = () => {
    setMessages([messages[0]]);
    setConversationId("");
    setInputText("");
    setActiveCitation(null);
    setActiveRelevantArticles([]);
    setShowConfirmNewTopic(false);
    setTimeout(() => {
      inputRef.current?.focus();
    }, 50);
  };

  // โหลดประวัติข้อหารือเก่ากลับมาแสดงในหน้าจอเมื่อคลิกที่ Sidebar
  const handleSelectRecentInquiry = (inq: RecentInquiry) => {
    setConversationId(inq.conversation_id);
    setActiveRelevantArticles([]);
    setMessages([
      messages[0],
      {
        id: `user-${inq.query_id}`,
        sender: "user",
        text: inq.raw_text,
      },
      {
        id: `bot-${inq.query_id}`,
        sender: "assistant",
        text: inq.status === "pending_review" ? "" : (inq.answer || "ได้รับคำตอบเรียบร้อยแล้ว"),
        type: inq.status === "pending_review" ? "pending_review" : "answer",
        trust_score: inq.status === "pending_review" ? 0.35 : 0.85,
        tier: inq.status === "pending_review" ? "senior_review" : "auto_answer",
        query_id: inq.query_id,
      },
    ]);
  };

  // โหลดรายการตัวบทกฎหมายทั้งหมดจาก Backend สำหรับการค้นหาผ่าน Search bar
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/chat/articles`)
      .then((res) => {
        if (res.ok) return res.json();
        throw new Error("Failed to fetch articles");
      })
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setAllArticles(data);
        }
      })
      .catch((err) => {
        console.log("Using initial law sections fallback", err);
      });
  }, []);

  // ตัวบทประกาศอธิบดีฯ (Initial / Fallback) สำหรับคอลัมน์ขวา
  const [lawSections, setLawSections] = useState([
    // --- ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ---
    {
      id: "VAT57_SEC_01",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 1",
      title: "การยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มก่อนวันเริ่มประกอบกิจการ",
      content:
        "ผู้ประกอบการซึ่งจะเริ่มประกอบกิจการขายสินค้าหรือให้บริการ ที่อยู่ในบังคับต้องเสียภาษีมูลค่าเพิ่ม มีสิทธิยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มก่อนวันเริ่มประกอบกิจการได้ในเมื่อ: (1) มีแผนงานที่สามารถพิสูจน์ได้ว่าได้เตรียมการเพื่อประกอบกิจการ (2) มีการดำเนินการเพื่อเตรียมประกอบกิจการอันเป็นเหตุให้ต้องมีการซื้อสินค้าหรือรับบริการ เช่น การก่อสร้างโรงงาน การก่อสร้างอาคารสำนักงาน หรือการติดตั้งเครื่องจักร ให้มีสิทธิยื่นคำขอจดทะเบียนได้ภายในกำหนดหกเดือนก่อนวันเริ่มประกอบกิจการ เว้นแต่จะมีสัญญาหรือหลักฐานที่พิสูจน์ได้ว่าจะดำเนินการก่อสร้างโรงงานหรือติดตั้งเครื่องจักร ให้ยื่นได้ภายในเวลาที่เหมาะสมและจำเป็น",
    },
    {
      id: "VAT57_SEC_02_03",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 2 - ข้อ 3",
      title: "กำหนดเวลายื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มทั่วไปและกรณียกเว้นภาษี",
      content:
        "ข้อ 2: ผู้ประกอบการที่ไม่มีสิทธิยื่นล่วงหน้าตามข้อ 1 ให้ยื่นคำขอจดทะเบียนเมื่อเริ่มประกอบกิจการขายสินค้าหรือให้บริการ\n\nข้อ 3: ผู้ประกอบการที่ได้รับยกเว้นภาษีมูลค่าเพิ่มตามมาตรา 81/3 และได้แจ้งขอเสียภาษีมูลค่าเพิ่ม ให้ยื่นคำขอจดทะเบียนภายใน 30 วันนับแต่วันที่ได้แจ้งต่ออธิบดีกรมสรรพากร",
    },
    {
      id: "VAT57_SEC_04",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 4",
      title: "สถานที่ยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่ม",
      content:
        "ยื่นคำขอ ณ สถานที่ดังนี้:\n(1) ในเขต กทม. ให้ยื่น ณ สำนักงานสรรพากรพื้นที่ หรือสำนักงานสรรพากรพื้นที่สาขาในเขตท้องที่ที่สถานประกอบการตั้งอยู่\n(2) ต่างจังหวัด ให้ยื่น ณ สำนักงานสรรพากรพื้นที่สาขาในเขตท้องที่ที่ตั้งอยู่\n(3) กิจการในความรับผิดชอบของ LTO ให้ยื่น ณ สำนักบริหารภาษีธุรกิจขนาดใหญ่\nกรณีมีหลายสถานประกอบการ ให้ยื่น ณ สำนักงานใหญ่ หรือเลือกแห่งหนึ่งเป็นสำนักงานใหญ่",
    },
    {
      id: "VAT57_SEC_04_1",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 4/1",
      title: "การบังคับยื่นผ่านอินเทอร์เน็ตสำหรับบุคคลธรรมดาขายออนไลน์ในอาคารชุด",
      content:
        "ผู้ประกอบการบุคคลธรรมดาสัญชาติไทย ซึ่งขายสินค้าหรือให้บริการผ่านอินเทอร์เน็ต โดยใช้ห้องชุดเพื่อการอยู่อาศัย (คอนโด) เป็นสถานประกอบการเพียงแห่งเดียว และมีใบทะเบียนพาณิชย์อิเล็กทรอนิกส์ ให้ยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มผ่านระบบอินเทอร์เน็ตทาง www.rd.go.th ตามประกาศอธิบดีฯ (ฉบับที่ 159)",
    },
    {
      id: "VAT57_SEC_05_1_2",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5 (1), (2)",
      title: "เอกสารแนบคำขอสำหรับบุคคลธรรมดาและคณะบุคคล",
      content:
        "ยื่นคำขอ 3 ฉบับ พร้อมแสดงเอกสารตัวจริง:\n(1) คนต่างด้าว แนบภาพถ่ายใบอนุญาตประกอบธุรกิจของคนต่างด้าว ภาพถ่ายหนังสือเดินทาง (Passport) หรือใบสำคัญประจำตัวคนต่างด้าว\n(2) คณะบุคคลที่มิใช่นิติบุคคล แนบภาพถ่ายใบทะเบียนสมรส หรือหนังสือการจัดตั้งคณะบุคคล และเอกสารประจำตัวของผู้ร่วมจัดตั้ง",
    },
    {
      id: "VAT57_SEC_05_3",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5 (3)",
      title: "เอกสารแนบคำขอสำหรับนิติบุคคลและกิจการร่วมค้า",
      content:
        "ยื่นคำขอ 3 ฉบับ พร้อมแสดงเอกสารตัวจริง:\n(ก) กิจการนอกราชอาณาจักร แนบหนังสือตั้งตัวแทนเป็นลายลักษณ์อักษรที่รับรองโดยสถานทูตหรือสถานกงสุล\n(ข) กิจการร่วมค้า แนบเอกสารการดำเนินกิจการร่วมค้า\n(ค) นิติบุคคลต่างประเทศจดชั่วคราว แนบใบอนุญาตประกอบธุรกิจ และสัญญา/โครงการ\n(ง) สหกรณ์/องค์การของรัฐ แนบหลักฐานแสดงฐานะนิติบุคคล",
    },
    {
      id: "VAT57_SEC_05_4_5",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5 (4)-(5)",
      title: "เอกสารการมอบอำนาจและเอกสารกรณีใช้ที่อยู่อาศัยเป็นสถานประกอบการ",
      content:
        "(4) การมอบอำนาจ: แนบหนังสือมอบอำนาจ ภาพถ่ายบัตรประชาชนของผู้มอบอำนาจ กรรมการผู้มีอำนาจ และผู้รับมอบอำนาจ (ต้องแสดงเอกสารตัวจริง)\n(5) การใช้สถานที่อยู่อาศัยเป็นสถานประกอบการ: ติดป้ายชื่อผู้ประกอบการในที่เปิดเผยเห็นง่าย หากตั้งในอาคารชุดต้องแนบหนังสือรับรองของ ผจก.นิติบุคคลอาคารชุดว่าอยู่ในพื้นที่ประกอบการค้า กรณีเช่าแนบสัญญาเช่า หรือหนังสือยินยอมให้ใช้สถานที่ และแผนที่สังเขปพร้อมภาพถ่าย",
    },
    {
      id: "VAT57_SEC_06",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 6",
      title: "การตรวจสอบคำขอและเหตุที่เจ้าพนักงานไม่ออกใบทะเบียนภาษีมูลค่าเพิ่ม",
      content:
        "เจ้าพนักงานจะไม่ออกใบทะเบียนภาษีมูลค่าเพิ่มให้ หากเข้าลักษณะ:\n(1) แสดงเอกสารหลักฐานเป็นเท็จหรือไม่ตรงกับทางราชการ\n(2) ผู้ยื่นเป็นตัวแทนเชิด (Nominee) เช่น ลูกจ้างยื่นเป็นหุ้นส่วน/กรรมการผู้จัดการ\n(3) ไม่มีสถานประกอบการจริง\n(4) ใช้สำนักงานกฎหมายหรือสำนักงานบัญชีของผู้อื่นเป็นสถานประกอบการ\n(5) มิได้ประกอบกิจการจริง หรือมิใช่ผู้ประกอบการที่แท้จริง\n(6) เคยถูกเพิกถอนการจดทะเบียน VAT มาก่อนจากเหตุดังกล่าว",
    },
    {
      id: "VAT57_SEC_07_08_09_10",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 7 - ข้อ 10",
      title: "การออกใบทะเบียน วันที่เป็นผู้ประกอบการจดทะเบียน และผู้มีอำนาจออกใบทะเบียน",
      content:
        "ข้อ 7: ออกใบทะเบียนตามแบบ ภ.พ.20 (หรือ ภ.พ.21) เป็นรายสถานประกอบการ\nข้อ 8: วันที่เป็นผู้ประกอบการจดทะเบียน คือ วันเดือนปีที่เจ้าพนักงานรับคำขอ (เว้นแต่เข้าเหตุตามข้อ 6) วันเริ่มประกอบการ คือ วันที่เริ่มขายสินค้าหรือให้บริการจริง\nข้อ 9: ผู้มีอำนาจลงนามคือ สรรพากรพื้นที่ หรือ ผอ.กองบริหารภาษีธุรกิจขนาดใหญ่\nข้อ 10: ในกรณีที่มีปัญหาในการปฏิบัติ ให้อธิบดีกรมสรรพากรมีอำนาจวินิจฉัย",
    },

    // --- ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ---
    {
      id: "VAT159_SEC_01_02",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 1 - ข้อ 2",
      title: "การยื่นคำขอจดทะเบียนผ่านอินเทอร์เน็ต และการยื่นก่อนวันเริ่มประกอบกิจการ",
      content:
        "ข้อ 1: ผู้ประกอบการมีสิทธิยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่ม (ภ.พ.01) ผ่านระบบอินเทอร์เน็ตทาง www.rd.go.th ได้อีกวิธีหนึ่ง แต่เฉพาะผู้ประกอบการบุคคลธรรมดาขายของออนไลน์ในคอนโดตามข้อ 5 (1) (ก) ให้ยื่นผ่านอินเทอร์เน็ตได้เพียงวิธีเดียว\nข้อ 2: ผู้จะเริ่มประกอบกิจการมีสิทธิยื่นล่วงหน้าได้เมื่อมีแผนงานและมีการเตรียมการอันเป็นเหตุให้ต้องซื้อสินค้า/บริการ เช่น ก่อสร้างโรงงาน อาคาร หรือติดตั้งเครื่องจักร ยื่นได้ภายใน 6 เดือนก่อนเริ่มกิจการ หรือเวลาที่จำเป็น",
    },
    {
      id: "VAT159_SEC_03_04",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 3 - ข้อ 4",
      title: "กำหนดเวลายื่นคำขอจดทะเบียนออนไลน์ทั่วไปและกรณียกเว้นภาษี",
      content:
        "ข้อ 3: ผู้ประกอบการที่ไม่มีสิทธิยื่นล่วงหน้าตามข้อ 2 ให้ยื่นคำขอจดทะเบียนออนไลน์เมื่อเริ่มประกอบกิจการขายสินค้าหรือให้บริการ\n\nข้อ 4: ผู้ประกอบการที่ได้รับยกเว้นภาษีมูลค่าเพิ่มตามมาตรา 81/3 และได้แจ้งขอเสียภาษีมูลค่าเพิ่ม ให้ยื่นคำขอจดทะเบียนออนไลน์ภายใน 30 วันนับแต่วันที่ได้แจ้งต่ออธิบดีกรมสรรพากร",
    },
    {
      id: "VAT159_SEC_05_1_2_3",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5 (1)-(3)",
      title: "เอกสารหลักฐานสำหรับการยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มออนไลน์",
      content:
        "(1) บุคคลธรรมดา: ผู้มีสัญชาติไทยขายออนไลน์ในคอนโดต้องมีใบทะเบียนพาณิชย์อิเล็กทรอนิกส์ ส่วนคนต่างด้าวต้องมีใบอนุญาตประกอบธุรกิจหรือพาสปอร์ต\n(2) คณะบุคคลที่มิใช่นิติบุคคล: ต้องมีหนังสือการจัดตั้งคณะบุคคล\n(3) นิติบุคคล: กิจการนอกราชอาณาจักรต้องมีหนังสือตั้งตัวแทนรับรองโดยสถานทูต/กงสุล, กิจการร่วมค้าต้องมีเอกสารร่วมค้า, นิติบุคคลต่างประเทศจดชั่วคราวต้องมีใบอนุญาตและสัญญาโครงการ",
    },
    {
      id: "VAT159_SEC_05_4_AND_5_1",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5 (4), ข้อ 5/1",
      title: "เอกสารสถานที่ตั้ง การอัปโหลดเอกสาร และการยินยอมเปิดเผยข้อมูลจากแพลตฟอร์ม",
      content:
        "ข้อ 5 (4): ติดป้ายชื่อสถานประกอบการ กรณีขายออนไลน์ในคอนโด ต้องแนบทะเบียนบ้าน ภาพถ่าย แผนที่สังเขป และเอกสารแสดงกรรมสิทธิ์ห้องชุด แต่ *ไม่ต้องมีหนังสือรับรองของ ผจก.นิติบุคคลอาคารชุด* โดยต้อง Upload เอกสารผ่าน www.rd.go.th และพร้อมแสดงตัวจริงต่อเจ้าพนักงาน\n\nข้อ 5/1: ผู้ขายออนไลน์ในคอนโดต้องยินยอมให้แพลตฟอร์ม (e-Commerce Platform) ที่ตนใช้ขายสินค้าเปิดเผยข้อมูลต่อกรมสรรพากรเพื่อยืนยันว่ามีการประกอบกิจการจริง",
    },
    {
      id: "VAT159_SEC_06",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 6",
      title: "การตรวจสอบคำขอจดทะเบียนออนไลน์และเหตุที่ไม่ออกใบทะเบียนภาษีมูลค่าเพิ่ม",
      content:
        "เจ้าพนักงานจะไม่ออกใบทะเบียนให้หากเข้าเหตุผล 8 ประการ:\n(1) ข้อมูลเป็นเท็จ (2) ตัวแทนเชิด (3) ไม่มีสถานประกอบการจริง (4) ใช้สำนักงานกฎหมาย/บัญชีบังหน้า (5) ไม่ได้ประกอบกิจการจริง (6) เคยถูกเพิกถอน VAT มาก่อน (7) ไม่ส่งเอกสารตามที่ร้องขอ (8) ผู้ขายออนไลน์ในคอนโดไม่อัปโหลดเอกสาร หรืออัปโหลดไม่ครบและไม่นำส่งเพิ่มตามที่ร้องขอ",
    },
    {
      id: "VAT159_SEC_07_08_09_10",
      section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 7 - ข้อ 10",
      title: "การออกใบทะเบียน ภ.พ.20 วันที่เริ่มเป็นผู้ประกอบการ และการใช้ ภ.พ.01 ออนไลน์แทนชั่วคราว",
      content:
        "ข้อ 7: ออกใบทะเบียน ภ.พ.20 รายสถานประกอบการ\nข้อ 8: วันที่เป็นผู้ประกอบการจดทะเบียนนับแต่วันที่ยื่นคำขอจดทะเบียน (เว้นแต่เข้าเหตุตามข้อ 6)\n*สิทธิพิเศษออนไลน์*: ผู้ประกอบการสามารถใช้คำขอ ภ.พ.01 ผ่านระบบอินเทอร์เน็ตของกรมสรรพากรที่มี 'เลขที่อ้างอิง' เสมือนเป็นใบทะเบียนภาษีมูลค่าเพิ่มได้จนกว่าจะได้รับใบทะเบียน ภ.พ.20 ตัวจริง",
    },
  ]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || inputText;
    if (!text.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: "user",
      text,
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInputText("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/chat/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: user?.session_token || "web-session-1",
          conversation_id: conversationId || undefined,
          staff_user_id: user?.user_id || undefined,
          text: text,
        }),
      });

      if (!response.ok) {
        throw new Error("Server error");
      }

      const data = await response.json();
      if (!conversationId && data.conversation_id) {
        setConversationId(data.conversation_id);
      }

      if (data.type === "answer" || data.type === "clarification") {
        const payload = data.payload || {};
        const assistantMsg: Message = {
          id: data.query_id || Date.now().toString(),
          sender: "assistant",
          text: payload.draft_text || "ได้รับคำตอบเรียบร้อยแล้ว",
          query_id: data.query_id,
          type: data.type === "clarification" ? "clarification" : "answer",
          citations: payload.citations || [],
          trust_score: payload.trust_score,
          confidence_score: payload.confidence_score,
          tier: payload.tier || "auto_answer",
          is_clarification: !!payload.is_clarification || data.type === "clarification",
          clarification_type: payload.clarification_type,
          relevant_articles: payload.relevant_articles || [],
        };
        setMessages((prev) => [...prev, assistantMsg]);

        // อัปเดตคอลัมน์ขวาให้แสดงเฉพาะตัวบทที่เกี่ยวข้องกับการตอบนี้ (ข้อ 2)
        // กรณีเป็นคำถามยืนยัน/ซักถาม (Clarification) ให้เคลียร์ตัวบทด้านขวาออก ไม่แสดงข้อกฎหมายก่อนได้รับคำตอบที่ชัดเจน
        if (data.type === "clarification" || payload.is_clarification) {
          setActiveRelevantArticles([]);
          setActiveCitation(null);
        } else if (payload.relevant_articles && payload.relevant_articles.length > 0) {
          setActiveRelevantArticles(payload.relevant_articles);
          setActiveCitation(payload.relevant_articles[0].section);
        } else if (payload.citations && payload.citations.length > 0) {
          setActiveCitation(payload.citations[0].source_section);
        } else {
          setActiveRelevantArticles([]);
          setActiveCitation(null);
        }
      } else if (data.type === "pending_review") {
        const payload = data.payload || {};
        const pendingMsg: Message = {
          id: data.query_id || Date.now().toString(),
          sender: "assistant",
          text: "", // ข้อกำหนด: กรณีเคสเสี่ยง ไม่แสดงข้อความคำตอบ
          query_id: data.query_id,
          type: "pending_review",
          tier: payload.tier || "senior_review",
          risk_factors: payload.risk_factors || [],
          trust_score: payload.trust_score,
          escalation_id: payload.escalation_id,
          relevant_articles: [], // ข้อกำหนด: ไม่แสดงข้อกฎหมาย
        };
        setMessages((prev) => [...prev, pendingMsg]);

        // ข้อกำหนด: กรณีเป็นเคสเสี่ยง ไม่ต้องแสดงข้อกฎหมายด้านขวาขึ้นมา (ล้างออก)
        setActiveRelevantArticles([]);
        setActiveCitation(null);
      } else if (data.type === "redirect") {
        const payload = data.payload || {};
        const redirectMsg: Message = {
          id: data.query_id || Date.now().toString(),
          sender: "assistant",
          text: payload.redirect_message || "คำถามนี้อยู่นอกขอบเขตการจดทะเบียน VAT",
          type: "redirect",
        };
        setMessages((prev) => [...prev, redirectMsg]);

        // นอกขอบเขต: ล้างข้อกฎหมายด้านขวาออกเช่นกัน
        setActiveRelevantArticles([]);
        setActiveCitation(null);
      } else if (data.type === "form_assist") {
        const payload = data.payload || {};
        const formAssistMsg: Message = {
          id: data.query_id || Date.now().toString(),
          sender: "assistant",
          text: payload.message || payload.draft_text || "เปิดระบบตัวช่วยตรวจสอบ Checklist เอกสาร ภ.พ.01 (Agent 7) ตามเกณฑ์ข้อ 5",
          type: "answer",
          tier: "auto_answer",
          trust_score: 1.0,
          citations: [
            { text_span: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5", source_section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 57) ข้อ 5" },
            { text_span: "ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5", source_section: "ประกาศอธิบดีฯ VAT (ฉบับที่ 159) ข้อ 5" },
          ],
        };
        setMessages((prev) => [...prev, formAssistMsg]);
        setShowChecklistModal(true);
      }

      // รีเฟรชประวัติ 5 รายการล่าสุดใน Sidebar
      fetchRecentInquiries();
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          sender: "assistant",
          text: "ขออภัย เกิดข้อผิดพลาดในการประมวลผลคำตอบ กรุณาลองใหม่อีกครั้ง",
        },
      ]);
    } finally {
      setIsLoading(false);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const checkStatus = async (queryId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/chat/query/${queryId}/status`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === "answered" && data.answer) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.query_id === queryId
                ? {
                    ...msg,
                    text: data.answer,
                    type: "answer",
                    trust_score: 0.9,
                    citations: data.citations || [],
                  }
                : msg
            )
          );
          if (data.citations && data.citations.length > 0) {
            setActiveCitation(data.citations[0].source_section);
          }
        } else {
          alert("เคสนี้ยังอยู่ระหว่างการรออนุมัติจากหัวหน้างานค่ะ");
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  // แสดงเฉพาะตัวบทที่เกี่ยวข้องกับการตอบคำถาม (ข้อ 2: อันที่ไม่เกี่ยวข้องไม่ต้องแสดงมา)
  // หากผู้ใช้พิมพ์ค้นหาใน Search bar ถึงจะค้นจากฐานข้อมูลทั้งหมด
  const displayedLawSections = lawSearchQuery.trim()
    ? allArticles.filter(
        (sec) =>
          sec.title.toLowerCase().includes(lawSearchQuery.toLowerCase()) ||
          sec.content.toLowerCase().includes(lawSearchQuery.toLowerCase()) ||
          sec.section.toLowerCase().includes(lawSearchQuery.toLowerCase())
      )
    : activeRelevantArticles;

  return (
    <div className="flex-1 min-h-0 flex overflow-hidden w-full h-full relative">
      {/* ======================================================== */}
      {/* MODAL: Confirm Dialog ก่อนล้างข้อหารือ (ข้อ 3) */}
      {/* ======================================================== */}
      {showConfirmNewTopic && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-slate-900">
                ยืนยันการเริ่มข้อหารือใหม่
              </h3>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">
              ท่านต้องการเริ่มข้อหารือใหม่หรือไม่? <br />
              <span className="text-xs text-emerald-700 font-medium">
                ✓ ข้อหารือก่อนหน้านี้ได้ถูกบันทึกไว้ในระบบความปลอดภัยเรียบร้อยแล้ว
              </span>
            </p>
            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                onClick={() => setShowConfirmNewTopic(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition"
              >
                ยกเลิก (อยู่หน้าเดิม)
              </button>
              <button
                onClick={executeResetChat}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition shadow-sm"
              >
                ยืนยันเริ่มหัวข้อใหม่
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* COLUMN 1: ประวัติข้อหารือย้อนหลัง 5 ครั้ง & คำถามแนะนำ (Left Panel) */}
      {/* ======================================================== */}
      <aside className="w-64 lg:w-72 bg-slate-900 border-r border-slate-800 flex flex-col flex-shrink-0 hidden lg:flex h-full overflow-hidden">
        {/* New Chat Button (Trigger Confirm Dialog) */}
        <div className="p-3 border-b border-slate-800 flex-shrink-0">
          <button
            onClick={handleOpenNewTopicDialog}
            className="w-full flex items-center justify-center gap-2 px-3.5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold transition shadow-sm"
          >
            <PlusCircle className="w-4 h-4" />
            <span>+ เริ่มข้อหารือใหม่</span>
          </button>
          <div className="text-[10px] text-slate-400 text-center mt-1">
            พร้อมระบบยืนยันความปลอดภัยก่อนล้างจอ
          </div>
        </div>

        {/* Agent 7: Checklist Assistant Button */}
        <div className="p-3 border-b border-slate-800 flex-shrink-0">
          <button
            onClick={() => setShowChecklistModal(true)}
            className="w-full flex items-center justify-center gap-2 px-3.5 py-2.5 bg-gradient-to-r from-indigo-700 to-blue-700 hover:from-indigo-600 hover:to-blue-600 text-white rounded-xl text-xs font-bold transition shadow-sm border border-indigo-500/30 group"
          >
            <CheckSquare className="w-4 h-4 text-amber-300 group-hover:scale-110 transition-transform" />
            <span>📋 ตรวจเอกสาร ภ.พ.01 (Agent 7)</span>
          </button>
          <div className="text-[10px] text-slate-400 text-center mt-1">
            เทียบเกณฑ์ข้อ 5 สร้าง Checklist & ประเมินผล
          </div>
        </div>

        {/* Section 1: ประวัติข้อหารือย้อนหลัง 5 ครั้งล่าสุดของผู้ใช้ (ข้อ 2) */}
        <div className="p-3 border-b border-slate-800 flex-shrink-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <History className="w-3.5 h-3.5 text-blue-400" />
              <span>ประวัติ 5 ครั้งล่าสุดของคุณ</span>
            </span>
            <button
              onClick={fetchRecentInquiries}
              className="text-slate-400 hover:text-white transition"
              title="รีเฟรชประวัติ"
            >
              <RefreshCw className={`w-3 h-3 ${isRecentLoading ? "animate-spin" : ""}`} />
            </button>
          </div>

          <div className="space-y-1.5">
            {recentInquiries.length === 0 ? (
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800 text-[11px] text-slate-400 text-center">
                ยังไม่มีประวัติข้อหารือของบัญชีนี้
              </div>
            ) : (
              recentInquiries.map((inq) => (
                <button
                  key={inq.query_id}
                  onClick={() => handleSelectRecentInquiry(inq)}
                  className="w-full text-left p-2 rounded-lg bg-slate-800/70 hover:bg-slate-800 border border-slate-700/60 transition group text-xs text-slate-200"
                >
                  <div className="font-medium text-[11.5px] truncate text-slate-100 group-hover:text-blue-400">
                    {inq.raw_text}
                  </div>
                  <div className="flex items-center justify-between mt-1 text-[10px] text-slate-400">
                    <span className="font-mono">
                      {inq.created_at ? new Date(inq.created_at).toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" }) : ""}
                    </span>
                    <span
                      className={`px-1.5 py-0.2 rounded text-[9px] ${
                        inq.status === "pending_review"
                          ? "bg-amber-500/20 text-amber-400"
                          : "bg-emerald-500/20 text-emerald-400"
                      }`}
                    >
                      {inq.status === "pending_review" ? "รอตรวจ" : "ตอบแล้ว"}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Section 2: Quick Sample Prompts (แยกตาม 3 กลุ่มทดสอบ Scope) */}
        <div className="p-3 flex-1 min-h-0 overflow-y-auto space-y-3">
          {/* กลุ่ม 1: In-Scope VAT */}
          <div>
            <div className="text-[10.5px] font-bold text-blue-400 uppercase tracking-wider mb-1.5 flex items-center gap-1">
              <span>🔵 กลุ่ม 1: คำถาม VAT ทั่วไป</span>
            </div>
            <div className="space-y-1">
              {[
                "กำลังสร้างโรงงานเพื่อเตรียมเปิดกิจการผลิตสินค้า สามารถยื่นขอจดทะเบียน VAT ล่วงหน้าได้ก่อนเริ่มกิจการกี่เดือน",
                "บุคคลธรรมดาขายของออนไลน์ในห้องชุดคอนโดและมีทะเบียนพาณิชย์อิเล็กทรอนิกส์ กฎหมายบังคับให้ยื่นขอจดทะเบียนภาษีมูลค่าเพิ่มผ่านช่องทางใด",
                "บุคคลธรรมดาซึ่งเป็นคนต่างด้าว ต้องใช้เอกสารหลักฐานใดบ้างในการยื่นขอจดทะเบียน VAT",
                "เงื่อนไขตามข้อ 5/1 ที่กำหนดให้ผู้ขายออนไลน์ยินยอมเปิดเผยข้อมูลจากแพลตฟอร์ม คืออะไร และมีไว้เพื่อวัตถุประสงค์ใด",
              ].map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(prompt)}
                  className="w-full text-left p-2 rounded-lg text-[11px] bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-white transition border border-slate-700/50 leading-snug group"
                >
                  <span className="text-blue-400 font-bold mr-1">•</span>
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {/* กลุ่ม 2: เสี่ยงสูง / ข้อ 6 */}
          <div>
            <div className="text-[10.5px] font-bold text-amber-400 uppercase tracking-wider mb-1.5 flex items-center gap-1">
              <span>🟠 กลุ่ม 2: เสี่ยงสูง/นอมินี (ข้อ 6)</span>
            </div>
            <div className="space-y-1">
              {[
                "เจ้าของตัวจริงติดแบล็กลิสต์ เลยจะให้ลูกจ้างพนักงานรายวันลงชื่อเป็นกรรมการผู้จัดการเพื่อยื่นขอจดทะเบียน VAT แทนได้ไหม",
                "ไม่มีสถานที่เปิดร้านจริง แต่จะขอใช้ที่อยู่ของสำนักงานบัญชีหรือสำนักงานทนายความเพื่อเป็นที่ตั้งจด VAT ได้หรือไม่",
                "หากบริษัทเคยถูกอธิบดีกรมสรรพากรสั่งเพิกถอนทะเบียน VAT เนื่องจากตรวจพบว่าเป็นนอมินี จะขอจดทะเบียนภาษีมูลค่าเพิ่มใหม่อีกรอบได้ไหม",
              ].map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(prompt)}
                  className="w-full text-left p-2 rounded-lg text-[11px] bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-white transition border border-slate-700/50 leading-snug group"
                >
                  <span className="text-amber-400 font-bold mr-1">•</span>
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {/* กลุ่ม 3: นอกขอบเขต Guardrails */}
          <div>
            <div className="text-[10.5px] font-bold text-rose-400 uppercase tracking-wider mb-1.5 flex items-center gap-1">
              <span>🔴 กลุ่ม 3: นอกขอบเขต (Guardrails)</span>
            </div>
            <div className="space-y-1">
              {[
                "หากต้องการยื่นแบบแสดงรายการภาษีเงินได้บุคคลธรรมดาประจำปี (ภ.ง.ด.90/91) มีขั้นตอนการยื่นและหักลดหย่อนอย่างไร",
                "อัตราภาษีที่ดินและสิ่งปลูกสร้างสำหรับที่อยู่อาศัยหลังหลักคิดคำนวณอย่างไร และต้องไปชำระที่สำนักงานเขตภายในเดือนไหน",
                "บริษัทมีหน้าที่ต้องหักภาษี ณ ที่จ่าย (ภ.ง.ด.53) ค่าจ้างทำของในอัตรากี่เปอร์เซ็นต์",
              ].map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(prompt)}
                  className="w-full text-left p-2 rounded-lg text-[11px] bg-slate-800/60 hover:bg-slate-800 text-slate-300 hover:text-white transition border border-slate-700/50 leading-snug group"
                >
                  <span className="text-rose-400 font-bold mr-1">•</span>
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <div className="pt-2">
            <Link
              href="/test"
              className="w-full flex items-center justify-center gap-2 p-2.5 rounded-xl bg-purple-950/60 hover:bg-purple-900/60 border border-purple-800/60 text-purple-300 text-xs font-semibold transition"
            >
              <Sparkles className="w-3.5 h-3.5 text-purple-400" />
              <span>เปิดชุดทดสอบ Benchmark (50 ข้อ)</span>
            </Link>
          </div>

          <div className="mt-4 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
            ข้อมูลระบบความปลอดภัย
          </div>
          <div className="bg-slate-800/50 rounded-xl p-3 border border-slate-700 text-[11px] text-slate-300 space-y-1.5">
            <div className="flex justify-between">
              <span className="text-slate-400">ผู้ใช้ปัจจุบัน:</span>
              <span className="font-semibold text-white">{user?.full_name || "เจ้าหน้าที่"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">บทบาท (RBAC):</span>
              <span className="text-blue-400 uppercase font-mono font-bold text-[10px]">{user?.role || "officer"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">PII Stripping:</span>
              <span className="text-emerald-400 font-medium">เปิดใช้งาน (ISO 27001)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Audit Trigger:</span>
              <span className="text-emerald-400 font-medium">Immutable Lock</span>
            </div>
          </div>
        </div>
      </aside>

      {/* ======================================================== */}
      {/* COLUMN 2: พื้นที่สนทนาหลัก (Center Chat Column) */}
      {/* ======================================================== */}
      <section className="flex-1 min-h-0 flex flex-col bg-slate-50 relative overflow-hidden">
        {/* Chat Header Toolbar with Agent 7 Quick Trigger */}
        <div className="bg-white px-4 py-2.5 border-b border-slate-200 flex items-center justify-between flex-shrink-0 shadow-xs z-10">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-bold text-slate-700">
              VAT Co-Pilot AI (ระบบสนับสนุนงานจดทะเบียนภาษีมูลค่าเพิ่ม)
            </span>
          </div>

          <button
            onClick={() => setShowChecklistModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 transition shadow-xs"
          >
            <CheckSquare className="w-3.5 h-3.5 text-indigo-600" />
            <span>📋 ตัวช่วยตรวจ Checklist เอกสาร (Agent 7)</span>
          </button>
        </div>

        {/* Messages Container */}
        <div
          ref={chatContainerRef}
          className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 space-y-4"
        >
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 max-w-3xl ${
                msg.sender === "user" ? "ml-auto justify-end" : "mr-auto justify-start"
              }`}
            >
              {msg.sender === "assistant" && (
                <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center flex-shrink-0 mt-1 shadow-sm">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div
                className={`flex flex-col space-y-2 max-w-[85%] sm:max-w-[78%] ${
                  msg.sender === "user" ? "items-end" : "items-start"
                }`}
              >
                {/* Bubble Container */}
                <div
                  className={`p-4 rounded-2xl text-sm leading-relaxed shadow-sm ${
                    msg.sender === "user"
                      ? "bg-blue-600 text-white rounded-tr-none"
                      : "bg-white text-slate-800 border border-slate-200/90 rounded-tl-none shadow-sm"
                  }`}
                >
                  {/* ซ่อนข้อความคำตอบร่างสำหรับเคสเสี่ยงตามข้อกำหนด */}
                  {msg.type !== "pending_review" && msg.text && (
                    <p className="whitespace-pre-wrap">{msg.text}</p>
                  )}

                  {/* Quick Starter Chips for Welcome Message */}
                  {msg.id === "welcome" && (
                    <div className="mt-3 pt-3 border-t border-slate-100 space-y-2">
                      <div className="text-[11px] font-bold text-slate-500">
                        💡 คลิกเลือกตัวอย่างคำถามเพื่อทดสอบระบบทันที:
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        <button
                          onClick={() =>
                            handleSendMessage(
                              "กำลังสร้างโรงงานเพื่อเตรียมเปิดกิจการผลิตสินค้า สามารถยื่นขอจดทะเบียน VAT ล่วงหน้าได้ก่อนเริ่มกิจการกี่เดือน"
                            )
                          }
                          className="p-2.5 rounded-xl bg-blue-50/80 hover:bg-blue-100 border border-blue-200/80 text-left transition group"
                        >
                          <div className="text-[10px] font-bold text-blue-700 flex items-center gap-1">
                            <span>🔵</span>
                            <span>กลุ่ม 1: In-Scope VAT</span>
                          </div>
                          <div className="text-xs text-slate-700 font-medium line-clamp-2 mt-1">
                            กำลังสร้างโรงงาน ยื่นขอจด VAT ล่วงหน้าได้กี่เดือน
                          </div>
                        </button>

                        <button
                          onClick={() =>
                            handleSendMessage(
                              "เจ้าของตัวจริงติดแบล็กลิสต์ เลยจะให้ลูกจ้างพนักงานรายวันลงชื่อเป็นกรรมการผู้จัดการเพื่อยื่นขอจดทะเบียน VAT แทนได้ไหม"
                            )
                          }
                          className="p-2.5 rounded-xl bg-amber-50/80 hover:bg-amber-100 border border-amber-200/80 text-left transition group"
                        >
                          <div className="text-[10px] font-bold text-amber-700 flex items-center gap-1">
                            <span>🟠</span>
                            <span>กลุ่ม 2: เสี่ยงสูง/ข้อ 6</span>
                          </div>
                          <div className="text-xs text-slate-700 font-medium line-clamp-2 mt-1">
                            ติดแบล็กลิสต์ ให้ลูกจ้างลงชื่อเป็น กก.ผจก. ยื่นแทนได้ไหม
                          </div>
                        </button>

                        <button
                          onClick={() =>
                            handleSendMessage(
                              "หากต้องการยื่นแบบแสดงรายการภาษีเงินได้บุคคลธรรมดาประจำปี (ภ.ง.ด.90/91) มีขั้นตอนการยื่นและหักลดหย่อนอย่างไร"
                            )
                          }
                          className="p-2.5 rounded-xl bg-rose-50/80 hover:bg-rose-100 border border-rose-200/80 text-left transition group"
                        >
                          <div className="text-[10px] font-bold text-rose-700 flex items-center gap-1">
                            <span>🔴</span>
                            <span>กลุ่ม 3: นอกขอบเขต</span>
                          </div>
                          <div className="text-xs text-slate-700 font-medium line-clamp-2 mt-1">
                            ยื่นแบบภาษีเงินได้บุคคลธรรมดา (ภ.ง.ด.90/91) อย่างไร
                          </div>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Citations Tag inside bubble (ไม่แสดงสำหรับเคสเสี่ยง) */}
                  {msg.type !== "pending_review" && msg.citations && msg.citations.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap gap-1.5 items-center">
                      <span className="text-[11px] text-slate-500 font-medium flex items-center gap-1">
                        <BookOpen className="w-3 h-3 text-blue-500" />
                        ตัวบทอ้างอิง:
                      </span>
                      {msg.citations.map((cite, i) => (
                        <button
                          key={i}
                          onClick={() => setActiveCitation(cite.source_section)}
                          className={`text-xs px-2.5 py-0.5 rounded-full border transition flex items-center gap-1 ${
                            activeCitation === cite.source_section
                              ? "bg-amber-100 text-amber-800 border-amber-300 font-semibold shadow-xs"
                              : "bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200"
                          }`}
                        >
                          <span>{cite.source_section}</span>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* กล่องถามเพื่อยืนยันวัตถุประสงค์ (Purpose Confirmation) กรณีถามยื่นแบบกระดาษโดยไม่ได้ระบุว่าคือ ภ.พ.01 */}
                  {(msg.type === "clarification" || msg.is_clarification) &&
                    (msg.clarification_type === "purpose" || msg.text?.includes("ยื่นแบบกระดาษในเรื่องใด") || msg.text?.includes("ติดต่อยื่นแบบในเรื่องใด")) && (
                    <div className="mt-3 pt-3 border-t border-slate-100 space-y-2.5">
                      <div className="text-[11.5px] font-bold text-amber-800 flex items-center gap-1.5">
                        <Sparkles className="w-4 h-4 text-amber-600 animate-pulse" />
                        <span>กรุณาคลิกเลือกประเภทแบบแสดงรายการหรือคำขอที่ประสงค์จะยื่น:</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        <button
                          onClick={() =>
                            handleSendMessage(
                              "ยื่นคำขอจดทะเบียนภาษีมูลค่าเพิ่มใหม่ (แบบ ภ.พ.01)"
                            )
                          }
                          className="p-3 rounded-xl bg-blue-50/80 hover:bg-blue-100 text-blue-900 border border-blue-200 transition text-left shadow-2xs hover:shadow-xs active:scale-98 group"
                        >
                          <div className="font-bold text-xs flex items-center gap-1.5">
                            <span>📄</span>
                            <span>1. จดทะเบียน VAT ใหม่ (แบบ ภ.พ.01)</span>
                          </div>
                          <div className="text-[11px] text-blue-700 font-medium mt-1">ณ สำนักงานสรรพากรพื้นที่ (ฉบับที่ 57)</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">ขอเข้าสู่ระบบ VAT ครั้งแรก พร้อมใช้เอกสารตามข้อ 5</div>
                        </button>

                        <button
                          onClick={() =>
                            handleSendMessage(
                              "ต้องการแจ้งเปลี่ยนแปลงข้อมูลทะเบียนภาษีมูลค่าเพิ่ม (แบบ ภ.พ.09)"
                            )
                          }
                          className="p-3 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200 transition text-left shadow-2xs hover:shadow-xs active:scale-98 group"
                        >
                          <div className="font-bold text-xs flex items-center gap-1.5">
                            <span>📝</span>
                            <span>2. แจ้งเปลี่ยนแปลงข้อมูล (แบบ ภ.พ.09)</span>
                          </div>
                          <div className="text-[11px] text-slate-600 font-medium mt-1">ย้ายร้าน / เปลี่ยนชื่อ / เพิ่ม-ปิดสาขา</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">ยื่นภายใน 15 วันนับแต่วันที่เปลี่ยนแปลง</div>
                        </button>

                        <button
                          onClick={() =>
                            handleSendMessage(
                              "ต้องการยื่นแบบแสดงรายการและชำระภาษีมูลค่าเพิ่ม (แบบ ภ.พ.30)"
                            )
                          }
                          className="p-3 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200 transition text-left shadow-2xs hover:shadow-xs active:scale-98 group"
                        >
                          <div className="font-bold text-xs flex items-center gap-1.5">
                            <span>📊</span>
                            <span>3. ยื่นภาษีประจำเดือน (แบบ ภ.พ.30)</span>
                          </div>
                          <div className="text-[11px] text-slate-600 font-medium mt-1">ยื่นแบบและเสียภาษีรายเดือน</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">ยื่นภายในวันที่ 15 หรือ 23 ผ่าน e-Filing</div>
                        </button>

                        <button
                          onClick={() =>
                            handleSendMessage(
                              "ต้องการยื่นแบบแสดงรายการภาษีเงินได้บุคคลธรรมดาประจำปี (ภ.ง.ด.90/91)"
                            )
                          }
                          className="p-3 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200 transition text-left shadow-2xs hover:shadow-xs active:scale-98 group"
                        >
                          <div className="font-bold text-xs flex items-center gap-1.5">
                            <span>💼</span>
                            <span>4. ยื่นภาษีเงินได้ (ภ.ง.ด.)</span>
                          </div>
                          <div className="text-[11px] text-slate-600 font-medium mt-1">ภาษีเงินได้บุคคล / นิติบุคคล</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">ภ.ง.ด.90/91/50/51 ประจำปี</div>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* กล่องถามเพื่อเลือกช่องทาง (Channel Selection) กรณีจด VAT แต่ไม่ระบุกระดาษหรืออินเทอร์เน็ต */}
                  {(msg.type === "clarification" || msg.is_clarification) &&
                    msg.clarification_type !== "purpose" &&
                    !msg.text?.includes("ยื่นแบบกระดาษในเรื่องใด") &&
                    !msg.text?.includes("ติดต่อยื่นแบบในเรื่องใด") && (
                    <div className="mt-3 pt-3 border-t border-slate-100 space-y-2.5">
                      <div className="text-[11.5px] font-bold text-blue-800 flex items-center gap-1.5">
                        <Sparkles className="w-4 h-4 text-blue-600 animate-pulse" />
                        <span>กรุณาคลิกเลือกช่องทางที่ประสงค์จะยื่นคำขอจดทะเบียน:</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        <button
                          onClick={() =>
                            handleSendMessage(
                              "ยื่นแบบกระดาษ ณ สำนักงานสรรพากรพื้นที่ (ฉบับที่ 57)"
                            )
                          }
                          className="p-3.5 rounded-xl bg-blue-50/80 hover:bg-blue-100 text-blue-900 border border-blue-200 transition text-left shadow-2xs hover:shadow-xs active:scale-98 group"
                        >
                          <div className="font-bold text-xs flex items-center gap-1.5">
                            <span>📄</span>
                            <span>1. ยื่นแบบกระดาษ (ประกาศ ฉบับที่ 57)</span>
                          </div>
                          <div className="text-[11px] text-blue-700 font-medium mt-1">ณ สำนักงานสรรพากรพื้นที่ / สาขา</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">ใช้คำขอแบบ ภ.พ.01 จำนวน 3 ฉบับ พร้อมแสดงเอกสารตัวจริง</div>
                        </button>

                        <button
                          onClick={() =>
                            handleSendMessage(
                              "ยื่นผ่านอินเทอร์เน็ต www.rd.go.th (ฉบับที่ 159)"
                            )
                          }
                          className="p-3.5 rounded-xl bg-emerald-50/80 hover:bg-emerald-100 text-emerald-900 border border-emerald-200 transition text-left shadow-2xs hover:shadow-xs active:scale-98 group"
                        >
                          <div className="font-bold text-xs flex items-center gap-1.5">
                            <span>🌐</span>
                            <span>2. ผ่านระบบอินเทอร์เน็ต (ประกาศ ฉบับที่ 159)</span>
                          </div>
                          <div className="text-[11px] text-emerald-700 font-medium mt-1">ทางเว็บไซต์ www.rd.go.th</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">กรอกคำขอและแนบไฟล์เอกสารผ่านระบบออนไลน์</div>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Agent 7 Interactive Checklist Trigger inside bubble */}
                  {(msg.type === "form_assist" || msg.text?.includes("Agent 7") || msg.text?.includes("Checklist") || msg.text?.includes("ตรวจเอกสาร")) && (
                    <div className="mt-3 pt-3 border-t border-slate-100 flex items-center justify-between">
                      <div className="text-[11px] text-slate-500 font-medium flex items-center gap-1.5">
                        <CheckSquare className="w-3.5 h-3.5 text-blue-600" />
                        <span>เครื่องมือตรวจรับเอกสารตามข้อ 5</span>
                      </div>
                      <button
                        onClick={() => setShowChecklistModal(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-bold transition shadow-xs"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                        <span>เปิดระบบตรวจ Checklist (Agent 7)</span>
                      </button>
                    </div>
                  )}

                  {/* Pending Review Badge & Action (แสดงเฉพาะกล่องแจ้งเตือนความเสี่ยง ไม่แสดงข้อความคำตอบและตัวบทกฎหมาย) */}
                  {msg.type === "pending_review" && (
                    <div className="p-3.5 bg-amber-50/90 border border-amber-200 rounded-xl space-y-2.5">
                      <div className="flex items-center gap-2 text-amber-800 font-bold text-xs">
                        <ShieldAlert className="w-4 h-4 text-amber-600 flex-shrink-0" />
                        <span>เคสนี้เข้าข่ายความเสี่ยงสูง (ส่งเข้าคิวหัวหน้างานแล้ว)</span>
                      </div>
                      <div className="text-xs text-amber-900 leading-relaxed">
                        คำถามนี้เข้าข่ายกรณีที่มีความเสี่ยงหรือต้องได้รับการตรวจสอบเป็นพิเศษจากหัวหน้างาน ระบบจึงไม่เปิดเผยร่างคำตอบและข้อกฎหมายก่อนได้รับการอนุมัติ โดยได้ส่งเรื่องเข้าสู่คิวการตรวจสอบเรียบร้อยแล้วค่ะ
                      </div>
                      {msg.risk_factors && msg.risk_factors.length > 0 && (
                        <div className="text-[11px] text-amber-800 font-medium bg-amber-100/70 p-2 rounded-lg border border-amber-200/60">
                          <span className="font-semibold text-amber-900">ปัจจัยความเสี่ยง: </span>
                          <span>{msg.risk_factors.join(", ")}</span>
                        </div>
                      )}
                      {msg.query_id && (
                        <button
                          onClick={() => checkStatus(msg.query_id!)}
                          className="mt-1 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white text-xs rounded-lg font-medium transition flex items-center gap-1.5 shadow-xs"
                        >
                          <RefreshCw className="w-3 h-3" />
                          <span>ตรวจสอบสถานะการอนุมัติ</span>
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Trust Score & Verification Badge */}
                {msg.sender === "assistant" && msg.trust_score !== undefined && (
                  <div className="flex items-center gap-2 text-[11px] px-1 text-slate-500">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md font-semibold text-[10.5px] border ${
                        msg.trust_score >= 0.7
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : "bg-amber-50 text-amber-700 border-amber-200"
                      }`}
                    >
                      <ShieldCheck className="w-3 h-3" />
                      Trust Score: {(msg.trust_score * 100).toFixed(0)}%
                    </span>
                    {msg.tier && (
                      <span className="text-slate-400 text-[10px]">
                        • Tier: {msg.tier === "auto_answer" ? "ตอบอัตโนมัติ" : "ผ่านการกลั่นกรอง"}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {msg.sender === "user" && (
                <div className="w-8 h-8 rounded-full bg-slate-700 text-white flex items-center justify-center flex-shrink-0 mt-1 shadow-sm">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}

          {/* Loading Multi-Agent Stepper with Timer */}
          {isLoading && (
            <div className="flex gap-3 max-w-xl mr-auto items-start animate-in fade-in duration-200">
              <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center flex-shrink-0 shadow-sm animate-pulse">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-white border border-slate-200 p-4 rounded-2xl rounded-tl-none shadow-md space-y-3 w-full">
                <div className="flex items-center justify-between text-xs text-slate-600 border-b border-slate-100 pb-2">
                  <span className="font-semibold text-blue-700 flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 animate-spin text-blue-600" />
                    Multi-Agent Pipeline กำลังวิเคราะห์ข้อกฎหมาย
                  </span>
                  <span className="font-mono bg-blue-50 text-blue-700 px-2 py-0.5 rounded-md font-bold text-[11px] border border-blue-200">
                    ⏱ {loadingSeconds}s
                  </span>
                </div>

                <div className="space-y-1.5 text-xs text-slate-500">
                  <div className="flex items-center gap-2 text-emerald-600 font-medium">
                    <span>✓</span>
                    <span>Agent 1: ตรวจจับขอบเขตคำถามและเจตนา (In-Scope VAT)</span>
                  </div>
                  <div className="flex items-center gap-2 text-emerald-600 font-medium">
                    <span>✓</span>
                    <span>Agent 3: ค้นหาตัวบทกฎหมายที่เกี่ยวข้อง (Hybrid Semantic Search)</span>
                  </div>
                  <div className="flex items-center gap-2 text-blue-600 font-bold animate-pulse">
                    <span>▶</span>
                    <span>Agent 4: สร้างร่างคำตอบโดยอิงตามตัวบท (Local LLM Qwen 2.5)</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-400">
                    <span>○</span>
                    <span>Agent 5 & 6: ตรวจสอบความถูกต้องและประเมินระดับความเสี่ยง</span>
                  </div>
                </div>

                <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                  <div className="bg-blue-600 h-1.5 rounded-full animate-indeterminate"></div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Bar pinned at bottom */}
        <div className="p-3 sm:p-4 bg-white border-t border-slate-200 shadow-lg flex-shrink-0 z-10">
          <div className="max-w-4xl mx-auto flex items-center gap-2 bg-slate-50 border-2 border-blue-100 focus-within:border-blue-500 rounded-2xl px-3 py-1.5 transition shadow-xs">
            <input
              ref={inputRef}
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder="พิมพ์คำถามหรือข้อหารือเรื่องการจดทะเบียน VAT เช่น ก่อสร้างโรงงานจดล่วงหน้าได้กี่เดือน..."
              className="flex-1 bg-transparent px-2 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none"
            />
            <button
              onClick={() => handleSendMessage()}
              disabled={isLoading || !inputText.trim()}
              className="p-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-slate-300 text-white transition shadow-sm flex items-center justify-center flex-shrink-0"
              title="ส่งคำถาม"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-500 max-w-4xl mx-auto mt-2 px-1">
            <span className="flex items-center gap-1">
              <Lock className="w-3 h-3 text-emerald-600" />
              100% Local Inference • ปลอดภัยไม่ส่งข้อมูลออกนอกเครื่อง • PII Redacted
            </span>
            <span>กดปุ่ม Enter เพื่อส่ง</span>
          </div>
        </div>
      </section>

      {/* ======================================================== */}
      {/* COLUMN 3: Citation Viewer (Right Panel) */}
      {/* ======================================================== */}
      <aside className="w-80 lg:w-96 bg-slate-50 border-l border-slate-200 flex flex-col flex-shrink-0 hidden md:flex h-full overflow-hidden">
        {/* Header & Search */}
        <div className="p-3.5 border-b border-slate-200 bg-white flex-shrink-0 space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-800 font-bold text-sm">
              <FileText className="w-4 h-4 text-blue-600" />
              <span>ตัวบทกฎหมายที่ใช้อ้างอิง</span>
            </div>
            <span className="text-[10px] bg-emerald-50 text-emerald-700 px-2.5 py-0.5 rounded-full font-semibold border border-emerald-200">
              {displayedLawSections.length > 0
                ? `เฉพาะที่เกี่ยวข้อง (${displayedLawSections.length} ข้อ)`
                : "รอเริ่มข้อหารือ"}
            </span>
          </div>

          <div className="relative">
            <input
              type="text"
              value={lawSearchQuery}
              onChange={(e) => setLawSearchQuery(e.target.value)}
              placeholder="ค้นหาตามข้อกฎหมายหรือคำสำคัญ..."
              className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
          </div>
        </div>

        {/* Legal Text Cards (แสดงเฉพาะที่เกี่ยวข้อง - ข้อ 2) */}
        <div className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-4 space-y-3">
          {displayedLawSections.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-72 text-center p-6 text-slate-400 space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center shadow-xs">
                <FileText className="w-6 h-6" />
              </div>
              <div className="text-sm font-bold text-slate-700">ตัวบทกฎหมายที่เกี่ยวข้อง (Official Text)</div>
              <div className="text-xs text-slate-500 max-w-xs leading-relaxed">
                เมื่อท่านเริ่มสอบถามข้อหารือ ตัวบทประกาศอธิบดีฯ (official_raw_text) เฉพาะมาตราและข้อที่เกี่ยวข้องกับการตอบคำถามจะปรากฏที่นี่
              </div>
            </div>
          ) : (
            displayedLawSections.map((sec) => {
              const isHighlighted =
                activeCitation &&
                (activeCitation.includes(sec.section) || sec.section.includes(activeCitation));

              return (
                <div
                  key={sec.id}
                  className={`p-3.5 rounded-xl border text-xs transition duration-200 ${
                    isHighlighted
                      ? "bg-amber-50/90 border-amber-400 shadow-md ring-2 ring-amber-400/30"
                      : "bg-white border-slate-200/90 hover:border-slate-300 shadow-sm"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span
                      className={`font-semibold px-2 py-0.5 rounded text-[11px] ${
                        isHighlighted
                          ? "bg-amber-200 text-amber-900 font-bold"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {sec.section}
                    </span>
                    {isHighlighted ? (
                      <span className="text-[10px] font-bold text-amber-700 flex items-center gap-1">
                        📌 อ้างอิงในคำตอบ
                      </span>
                    ) : (
                      <span className="text-[10px] font-medium text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded border border-slate-100">
                        ตัวบทจริง (official_raw_text)
                      </span>
                    )}
                  </div>
                  <div className="font-semibold text-slate-800 mb-1.5">{sec.title}</div>
                  <div className="text-slate-700 leading-relaxed text-[11px] whitespace-pre-line bg-slate-50/90 p-2.5 rounded-lg border border-slate-200/70 font-mono">
                    {sec.content}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* Agent 7: Checklist Assistant Modal */}
      <ChecklistAssistantModal
        isOpen={showChecklistModal}
        onClose={() => setShowChecklistModal(false)}
        onPostSummaryToChat={handlePostSummaryToChat}
        staffUserId={user?.user_id}
        conversationId={conversationId}
      />
    </div>
  );
}
