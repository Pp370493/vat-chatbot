/** @type {import('next').NextConfig} */
const { execSync } = require("child_process");

// รหัส commit ที่ build — แสดงท้ายหน้าแชท ใช้เช็คว่าเครื่องรันโค้ดเวอร์ชันล่าสุดแล้ว
let buildId = "unknown";
try {
  buildId = execSync("git rev-parse --short HEAD", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
} catch {}

const nextConfig = {
  reactStrictMode: true,
  env: { NEXT_PUBLIC_BUILD_ID: buildId },
};

module.exports = nextConfig;
