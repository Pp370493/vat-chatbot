import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "./context/AuthContext";
import { Navbar } from "./components/Navbar";

export const metadata: Metadata = {
  title: "Enterprise Tax Co-Pilot | กรมสรรพากร",
  description: "ระบบผู้ช่วย AI อัจฉริยะสำหรับเจ้าหน้าที่จดทะเบียนภาษีมูลค่าเพิ่ม (VAT)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="th" className="h-full">
      <body className="h-full flex flex-col bg-slate-50 antialiased overflow-hidden">
        <AuthProvider>
          {/* Header Bar with RBAC */}
          <Navbar />

          {/* Main Content Area */}
          <main className="flex-1 min-h-0 flex flex-col overflow-hidden">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
